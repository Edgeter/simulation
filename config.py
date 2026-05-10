from dataclasses import dataclass


@dataclass
class SimulationConfig:
    n_agents: int = 400
    n_ticks: int = 400
    governance_type: str = "human"  # human | ai | ai_strong
    seed: int = 42

    initial_resources: float = 10000.0
    network_m: int = 3
    shock_probability: float = 0.05

    # Satisfaction weights (must sum to 1.0)
    w_e: float = 0.24
    w_s: float = 0.16
    w_i: float = 0.12
    w_f: float = 0.14
    w_n: float = 0.12
    w_g: float = 0.14
    w_sec: float = 0.08

    # Human governance parameters
    corruption_base: float = 0.15
    oversight: float = 0.30
    nepotism_bias: float = 0.20
    adaptive_bonus_in_crisis: float = 0.15

    # AI governance parameters
    ai_objective: str = "gdp"  # gdp | fairness | happiness | stability
    hack_prob: float = 0.05
    ai_oversight_strength: float = 0.55
    ai_explainability: float = 0.60
    ai_anomaly_detection: float = 0.65
    ai_detection_base: float = 0.55
    ai_penalty_multiplier: float = 1.35
    ai_legal_arbitrage_share: float = 0.60
    ai_legal_exploit_scale: float = 0.0020
    ai_illegal_exploit_scale: float = 0.0050
    ai_patch_trigger_incidents: int = 3
    ai_patch_effectiveness: float = 0.22
    ai_patch_max_hardening: float = 0.70
    strong_ai_learning_rate: float = 0.08
    strong_ai_target_gini: float = 0.30
    strong_ai_target_u: float = 72.0
    strong_ai_target_corruption: float = 0.03
    conformity_penalty: float = 2.0
    information_overload_penalty: float = 0.6
    objective_mismatch: float = 0.04
    perception_lag: int = 2
    protocol_delay: int = 1

    # Tax and redistribution
    tax_rate: float = 0.15
    redistribution_rate: float = 0.70

    # Production
    prod_a: float = 8.0
    prod_b: float = 4.0
    prod_c: float = 2.0
