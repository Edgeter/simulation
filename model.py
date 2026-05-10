from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List, Tuple

import networkx as nx
import numpy as np

from agent import Agent
from config import SimulationConfig
from governance import AIGovernance, HumanGovernance, StrongAIGovernance
from metrics import avg_neighbor_u, behavior_entropy, clip01, gini


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


class SocietyModel:
    def __init__(self, cfg: SimulationConfig):
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg.seed)
        self.network = nx.barabasi_albert_graph(cfg.n_agents, cfg.network_m, seed=cfg.seed)
        self.neighbors = [list(self.network.neighbors(i)) for i in range(cfg.n_agents)]

        self.agents = self._init_agents(cfg.n_agents)
        self.resources = cfg.initial_resources
        self.legitimacy = 0.70
        self.tick = 0
        self.metrics_history: List[Dict[str, float]] = []

        if cfg.governance_type == "human":
            self.governance = HumanGovernance(cfg, self.rng)
        elif cfg.governance_type == "ai":
            self.governance = AIGovernance(cfg, self.rng)
        elif cfg.governance_type == "ai_strong":
            self.governance = StrongAIGovernance(cfg, self.rng)
        else:
            raise ValueError("governance_type must be 'human', 'ai' or 'ai_strong'")

    def _init_agents(self, n: int) -> List[Agent]:
        agents: List[Agent] = []
        for i in range(n):
            agents.append(
                Agent(
                    idx=i,
                    e=float(self.rng.uniform(30, 70)),
                    s=float(self.rng.uniform(20, 80)),
                    h=float(self.rng.uniform(20, 95)),
                    m=float(self.rng.uniform(-1, 1)),
                    i=float(self.rng.uniform(0.2, 0.8)),
                    u=float(self.rng.uniform(45, 75)),
                    p=float(self.rng.uniform(10, 60)),
                )
            )
        return agents

    def _shock(self) -> Tuple[bool, float]:
        if self.rng.random() >= self.cfg.shock_probability:
            return False, 1.0
        # factor < 1 means shock loss
        return True, float(self.rng.uniform(0.70, 0.92))

    def _production(self, shock_factor: float) -> float:
        total = 0.0
        for a in self.agents:
            h = a.h / 100.0
            e = a.e / 100.0
            deg = len(self.neighbors[a.idx])
            coop = min(1.0, deg / 20.0)
            prod = (self.cfg.prod_a * h + self.cfg.prod_b * np.sqrt(e) + self.cfg.prod_c * coop) * shock_factor
            total += prod
            a.e = _clip(a.e + 0.10 * prod, 0.0, 200.0)
        self.resources += total
        return total

    def _interaction(self) -> None:
        for i, nbrs in enumerate(self.neighbors):
            if not nbrs:
                continue
            j = int(self.rng.choice(nbrs))
            ai = self.agents[i]
            aj = self.agents[j]
            delta = 0.02 * (ai.h - aj.h)
            ai.e = _clip(ai.e + delta, 0.0, 200.0)
            aj.e = _clip(aj.e - delta, 0.0, 200.0)

    def _tax_and_redistribute(self) -> float:
        taxed = 0.0
        for a in self.agents:
            t = a.e * self.cfg.tax_rate
            a.e -= t
            taxed += t
        self.resources += taxed
        pool = taxed * self.cfg.redistribution_rate
        per = pool / len(self.agents)
        for a in self.agents:
            a.e += per
        self.resources -= pool
        return taxed

    def _update_satisfaction(self, freedom_factor: float, security_factor: float) -> None:
        e_vals = np.array([a.e for a in self.agents], dtype=float)
        s_vals = np.array([a.s for a in self.agents], dtype=float)
        i_vals = np.array([a.i for a in self.agents], dtype=float)
        m_vals = np.array([a.m for a in self.agents], dtype=float)
        g = gini(e_vals)

        e_min, e_max = float(e_vals.min()), float(e_vals.max())
        s_min, s_max = float(s_vals.min()), float(s_vals.max())
        n_u = avg_neighbor_u(self.agents, self.neighbors) / 100.0

        for a in self.agents:
            e_norm = 0.5 if e_max == e_min else (a.e - e_min) / (e_max - e_min)
            s_norm = 0.5 if s_max == s_min else (a.s - s_min) / (s_max - s_min)
            i_norm = clip01(a.i)
            f_norm = clip01((a.m + 1.0) / 2.0 * freedom_factor)
            g_norm = clip01(1.0 - g)
            sec_norm = clip01(security_factor)

            score = (
                self.cfg.w_e * e_norm
                + self.cfg.w_s * s_norm
                + self.cfg.w_i * i_norm
                + self.cfg.w_f * f_norm
                + self.cfg.w_n * clip01(n_u)
                + self.cfg.w_g * g_norm
                + self.cfg.w_sec * sec_norm
            )
            target_u = 100.0 * score
            a.u = _clip(0.85 * a.u + 0.15 * target_u, 0.0, 100.0)

    def _update_legitimacy(self, coercion: float) -> None:
        u_vals = np.array([a.u for a in self.agents], dtype=float)
        e_vals = np.array([a.e for a in self.agents], dtype=float)
        i_vals = np.array([a.i for a in self.agents], dtype=float)
        fairness = 1.0 - gini(e_vals)
        mean_u = float(u_vals.mean()) / 100.0
        var_u = float(u_vals.var()) / (100.0**2)
        trans = float(i_vals.mean())

        inst_quality = clip01(0.35 * mean_u + 0.25 * fairness + 0.20 * trans + 0.20 * (1.0 - var_u) - 0.15 * coercion)
        rho = 0.92
        self.legitimacy = _clip(rho * self.legitimacy + (1.0 - rho) * inst_quality, 0.0, 1.0)

    def _record_metrics(self, produced: float, gov, shock: bool) -> None:
        e_vals = np.array([a.e for a in self.agents], dtype=float)
        m_vals = np.array([a.m for a in self.agents], dtype=float)
        u_vals = np.array([a.u for a in self.agents], dtype=float)
        i_vals = np.array([a.i for a in self.agents], dtype=float)
        p_vals = np.array([a.p for a in self.agents], dtype=float)

        sorted_desc = np.sort(e_vals)[::-1]
        total_e = float(sorted_desc.sum())
        cumulative = np.cumsum(sorted_desc)
        if total_e <= 1e-9:
            holders_90_ratio = 0.0
        else:
            k = int(np.searchsorted(cumulative, 0.9 * total_e, side="left") + 1)
            holders_90_ratio = k / len(self.agents)

        q1 = float(np.quantile(e_vals, 1.0 / 3.0))
        q2 = float(np.quantile(e_vals, 2.0 / 3.0))
        low_ratio = float(np.mean(e_vals <= q1))
        high_ratio = float(np.mean(e_vals > q2))
        mid_ratio = max(0.0, 1.0 - low_ratio - high_ratio)

        corruption_rate = 0.0 if produced <= 1e-9 else gov.corruption_loss / produced
        metric = {
            "tick": self.tick,
            "governance": self.cfg.governance_type,
            "resources": self.resources,
            "produced": produced,
            "gini_e": gini(e_vals),
            "mean_u": float(u_vals.mean()),
            "median_u": float(np.median(u_vals)),
            "std_m": float(np.std(m_vals)),
            "behavior_entropy": behavior_entropy(m_vals),
            "info_mean": float(i_vals.mean()),
            "info_var": float(i_vals.var()),
            "efficiency": produced / len(self.agents),
            "corruption_rate": corruption_rate,
            "legal_arbitrage_gain": float(getattr(gov, "legal_arbitrage_gain", 0.0)),
            "illegal_arbitrage_gain": float(getattr(gov, "illegal_arbitrage_gain", 0.0)),
            "detected_illegal_cases": float(getattr(gov, "detected_illegal_cases", 0.0)),
            "legal_cases": float(getattr(gov, "legal_cases", 0.0)),
            "illegal_cases": float(getattr(gov, "illegal_cases", 0.0)),
            "holders_90_ratio": holders_90_ratio,
            "class_low_ratio": low_ratio,
            "class_mid_ratio": mid_ratio,
            "class_high_ratio": high_ratio,
            "mean_p": float(p_vals.mean()),
            "legitimacy": self.legitimacy,
            "shock": int(shock),
        }
        self.metrics_history.append(metric)

    def step(self) -> None:
        self.tick += 1
        is_shock, shock_factor = self._shock()

        produced = self._production(shock_factor)
        self._interaction()

        gov = self.governance.execute(
            self.agents,
            self.resources,
            crisis=is_shock,
            context={
                "legitimacy": self.legitimacy,
                "last_gini": self.metrics_history[-1]["gini_e"] if self.metrics_history else 0.35,
                "last_mean_u": self.metrics_history[-1]["mean_u"] if self.metrics_history else 60.0,
                "last_corruption_rate": self.metrics_history[-1]["corruption_rate"] if self.metrics_history else 0.04,
            },
        )
        self.resources = max(0.0, self.resources - gov.corruption_loss)

        self._tax_and_redistribute()
        self._update_satisfaction(gov.freedom_factor, gov.security_factor)

        coercion = 1.0 - gov.freedom_factor
        self._update_legitimacy(coercion)
        self._record_metrics(produced, gov, is_shock)

    def run(self) -> List[Dict[str, float]]:
        for _ in range(self.cfg.n_ticks):
            self.step()
        return self.metrics_history

    def final_summary(self) -> Dict[str, float]:
        window = self.metrics_history[max(0, len(self.metrics_history) - 50) :]
        if not window:
            return {}
        keys = [k for k in window[0].keys() if k not in ("tick", "governance")]
        summary: Dict[str, float] = {
            "governance": self.cfg.governance_type,
            "seed": self.cfg.seed,
            "n_agents": self.cfg.n_agents,
            "n_ticks": self.cfg.n_ticks,
            "config": asdict(self.cfg),
        }
        for k in keys:
            vals = [float(row[k]) for row in window]
            summary[f"avg_{k}"] = float(np.mean(vals))
        return summary
