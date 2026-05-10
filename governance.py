from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from agent import Agent
from config import SimulationConfig


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


@dataclass
class GovernanceResult:
    corruption_loss: float = 0.0
    freedom_factor: float = 1.0
    security_factor: float = 1.0
    legal_arbitrage_gain: float = 0.0
    illegal_arbitrage_gain: float = 0.0
    detected_illegal_cases: int = 0
    legal_cases: int = 0
    illegal_cases: int = 0


class HumanGovernance:
    def __init__(self, cfg: SimulationConfig, rng: np.random.Generator):
        self.cfg = cfg
        self.rng = rng

    def execute(self, agents: List[Agent], resources: float, crisis: bool = False, context: Optional[Dict] = None) -> GovernanceResult:
        result = GovernanceResult()
        elites = sorted(agents, key=lambda a: a.p, reverse=True)[: max(1, int(0.2 * len(agents)))]

        for a in elites:
            m_term = (1.0 - (a.m + 1.0) / 2.0)
            s_term = a.s / 100.0
            prob = _clip(self.cfg.corruption_base * (0.6 * m_term + 0.4 * s_term), 0.0, 0.8)
            if self.rng.random() < prob:
                amount = resources * (a.s / 100.0) * 0.01 * (1.0 - self.cfg.oversight)
                a.e += amount
                result.corruption_loss += amount

        promo_noise = self.rng.normal(0.0, 5.0)
        for a in agents:
            merit = 0.6 * a.h + 0.4 * a.s
            a.p = _clip(0.8 * a.p + 0.2 * merit + promo_noise * self.cfg.nepotism_bias, 0.0, 100.0)

        if crisis:
            result.security_factor = 1.0 + self.cfg.adaptive_bonus_in_crisis

        return result


class AIGovernance:
    def __init__(self, cfg: SimulationConfig, rng: np.random.Generator):
        self.cfg = cfg
        self.rng = rng
        self.crisis_countdown = 0
        self.patch_countdown = 0
        self.hardening = 0.0

    def _objective_bias(self) -> float:
        table = {
            "gdp": 0.22,
            "stability": 0.10,
            "happiness": 0.02,
            "fairness": -0.12,
        }
        return table.get(self.cfg.ai_objective, 0.0)

    def execute(self, agents: List[Agent], resources: float, crisis: bool = False, context: Optional[Dict] = None) -> GovernanceResult:
        result = GovernanceResult(freedom_factor=0.85)
        context = context or {}
        legitimacy = float(context.get("legitimacy", 0.7))

        objective_bias = self._objective_bias()
        governance_quality = _clip(
            0.45 * self.cfg.ai_oversight_strength
            + 0.30 * self.cfg.ai_explainability
            + 0.25 * self.cfg.ai_anomaly_detection,
            0.0,
            1.0,
        )

        vulnerability = _clip(1.0 - self.hardening + self.cfg.objective_mismatch + max(0.0, objective_bias) * 0.2, 0.1, 1.6)
        hack_prob = _clip(
            self.cfg.hack_prob
            * (1.0 - 0.70 * governance_quality)
            * vulnerability
            * (1.0 + max(0.0, objective_bias)),
            0.0,
            0.35,
        )
        detect_prob = _clip(
            self.cfg.ai_detection_base
            * (0.50 * self.cfg.ai_oversight_strength + 0.25 * self.cfg.ai_explainability + 0.25 * self.cfg.ai_anomaly_detection)
            * (0.85 + 0.30 * legitimacy)
            * (1.0 + self.hardening * 0.5),
            0.02,
            0.98,
        )

        legal_share = _clip(self.cfg.ai_legal_arbitrage_share + max(0.0, objective_bias) * 0.15, 0.15, 0.90)
        legal_scale = self.cfg.ai_legal_exploit_scale * (1.0 + max(0.0, objective_bias) * 0.7)
        illegal_scale = self.cfg.ai_illegal_exploit_scale * (1.0 + max(0.0, objective_bias) * 0.8)

        incidents = 0
        net_public_loss = 0.0

        if crisis:
            self.crisis_countdown = self.cfg.protocol_delay
        if self.crisis_countdown > 0:
            result.security_factor = 0.90
            self.crisis_countdown -= 1

        if self.patch_countdown > 0:
            self.patch_countdown -= 1
            if self.patch_countdown == 0:
                self.hardening = _clip(self.hardening + self.cfg.ai_patch_effectiveness, 0.0, self.cfg.ai_patch_max_hardening)

        for a in agents:
            if a.h > 90 and self.rng.random() < hack_prob:
                incidents += 1
                if self.rng.random() < legal_share:
                    gain = resources * legal_scale
                    a.e += gain
                    result.legal_cases += 1
                    result.legal_arbitrage_gain += gain
                else:
                    gain = resources * illegal_scale
                    a.e += gain
                    result.illegal_cases += 1
                    result.illegal_arbitrage_gain += gain
                    public_loss = gain
                    if self.rng.random() < detect_prob:
                        result.detected_illegal_cases += 1
                        confiscate = min(a.e, gain * self.cfg.ai_penalty_multiplier)
                        a.e -= confiscate
                        recovered = min(public_loss, confiscate)
                        public_loss -= recovered
                        a.p = _clip(a.p - 6.0, 0.0, 100.0)
                        a.u = _clip(a.u - 4.0, 0.0, 100.0)
                    net_public_loss += max(0.0, public_loss)

            a.i = 1.0
            a.u = _clip(a.u - self.cfg.information_overload_penalty, 0.0, 100.0)

        if incidents >= self.cfg.ai_patch_trigger_incidents and self.patch_countdown == 0:
            self.patch_countdown = self.cfg.perception_lag

        mean_m = float(np.mean([a.m for a in agents]))
        std_m = float(np.std([a.m for a in agents])) + 1e-6
        for a in agents:
            if abs(a.m - mean_m) > 2.0 * std_m:
                a.u = _clip(a.u - self.cfg.conformity_penalty, 0.0, 100.0)

            merit = 0.95 * a.h + 0.05 * a.s
            a.p = _clip(0.85 * a.p + 0.15 * merit, 0.0, 100.0)

        result.corruption_loss = net_public_loss
        return result


class StrongAIGovernance(AIGovernance):
    def __init__(self, cfg: SimulationConfig, rng: np.random.Generator):
        super().__init__(cfg, rng)
        self.objective_weights = {
            "efficiency": 0.30,
            "fairness": 0.30,
            "happiness": 0.25,
            "integrity": 0.15,
        }

    def _normalize_weights(self) -> None:
        total = sum(self.objective_weights.values())
        if total <= 1e-9:
            self.objective_weights = {"efficiency": 0.25, "fairness": 0.25, "happiness": 0.25, "integrity": 0.25}
            return
        for k in list(self.objective_weights.keys()):
            self.objective_weights[k] /= total

    def _learn_from_feedback(self, context: Dict) -> None:
        lr = self.cfg.strong_ai_learning_rate
        last_gini = float(context.get("last_gini", 0.35))
        last_u = float(context.get("last_mean_u", 60.0))
        last_cor = float(context.get("last_corruption_rate", 0.04))

        err_gini = last_gini - self.cfg.strong_ai_target_gini
        err_u = self.cfg.strong_ai_target_u - last_u
        err_cor = last_cor - self.cfg.strong_ai_target_corruption

        self.objective_weights["fairness"] += lr * max(0.0, err_gini)
        self.objective_weights["happiness"] += lr * max(0.0, err_u / 100.0)
        self.objective_weights["integrity"] += lr * max(0.0, err_cor)

        pressure = max(0.0, (self.cfg.strong_ai_target_u - last_u) / 100.0)
        self.objective_weights["efficiency"] += lr * pressure * 0.5
        self._normalize_weights()

        self.cfg.ai_oversight_strength = _clip(0.45 + 0.5 * self.objective_weights["integrity"], 0.2, 0.95)
        self.cfg.ai_anomaly_detection = _clip(0.45 + 0.45 * self.objective_weights["integrity"], 0.2, 0.95)
        self.cfg.ai_explainability = _clip(0.45 + 0.45 * self.objective_weights["fairness"], 0.2, 0.95)
        self.cfg.information_overload_penalty = _clip(0.7 - 0.4 * self.objective_weights["happiness"], 0.2, 1.2)
        self.cfg.conformity_penalty = _clip(2.4 - 1.4 * self.objective_weights["fairness"], 0.6, 2.8)
        self.cfg.objective_mismatch = _clip(0.06 - 0.035 * self.objective_weights["fairness"], 0.01, 0.08)

    def execute(self, agents: List[Agent], resources: float, crisis: bool = False, context: Optional[Dict] = None) -> GovernanceResult:
        context = context or {}
        self._learn_from_feedback(context)
        return super().execute(agents, resources, crisis=crisis, context=context)
