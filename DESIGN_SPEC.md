# Governance Simulation Design Spec

## 1) Objective and Comparison Logic

This project builds an agent-based simulation to compare two governance paradigms under identical initial conditions:

- Human Governance (person-centric, adaptive, noisy)
- AI Governance (algorithm-centric, consistent, objective-driven)

Only the governance function differs between scenarios. All other components (initial distributions, network topology, shocks, production logic, random seed policy) are controlled.

Core research goals:

1. Compare trade-offs across fairness, efficiency, freedom, resilience, corruption, and happiness.
2. Identify parameter regions where one governance mode dominates.
3. Test transition dynamics (human -> AI) and estimate an optimal switching window.

---

## 2) Model Structure

### 2.1 Agent State Vector

Each agent `i` has:

- `E_i` economic capital in `[0, 100]`
- `S_i` social capital in `[0, 100]`
- `H_i` human capital in `[0, 100]`
- `M_i` moral value in `[-1, 1]`
- `I_i` information transparency in `[0, 1]`
- `U_i` subjective well-being in `[0, 100]`
- `P_i` power in `[0, 100]`

Initialization rules:

- Same random seed set per paired experiment.
- Same distribution family and parameters for both governance types.
- Optional inequality presets: equal / moderate / extreme.

### 2.2 Environment Layer

- Total resource pool `R(t)`.
- Social network: Barabasi-Albert graph.
- Event queue: random shocks (disaster, technology, war, external boom).

### 2.3 Tick Pipeline

1. Production
2. Network interaction (trade, cooperation, conflict)
3. Governance execution
4. Tax and redistribution
5. Mobility update (`P` transitions)
6. Satisfaction update (`U`)
7. Exogenous shock handling

---

## 3) Governance Functions (Refined)

### 3.1 Human Governance

Mechanisms:

- Elite concentration by top `P` quantile.
- Corruption probability increases with high `S`, low `M`, low oversight.
- Policy implementation includes execution noise.
- Promotion mixes merit and connections.
- Crisis-mode flexibility bonus (important for resilience hypothesis).

Refined parameters:

- `corruption_base = 0.15`
- `oversight = 0.30`
- `nepotism_bias = 0.20`
- `adaptive_bonus_in_crisis = 0.10` to `0.30`

### 3.2 AI Governance

Mechanisms:

- Objective optimization (GDP / GINI / Happiness / Stability).
- Near-zero classic corruption, but rule-exploit channel exists.
- High transparency with possible information overload.
- Promotion strongly merit-oriented.
- Conformity pressure on moral outliers.

Critical realism add-ons (must include to avoid unfair advantage):

- Objective misspecification error (`objective_mismatch`).
- State-estimation delay (`perception_lag`).
- Crisis protocol delay (`protocol_delay`).

Refined parameters:

- `hack_prob = 0.05`
- `conformity_penalty = 2.0`
- `information_overload_penalty = 0.5` to `2.0`
- `objective_mismatch = 0.02` to `0.10`
- `perception_lag = 1` to `5` ticks

---

## 4) Dynamics and Equations

### 4.1 Production

`prod_i(t) = f(H_i, E_i, network_support_i, shock_factor_t)`

Baseline option:

`prod_i = a * H_i_norm + b * sqrt(E_i_norm) + c * coop_gain_i`

### 4.2 Satisfaction Update

Before aggregation, normalize each term to `[0,1]`.

`U_i(t+1) = clip_0_100( wE*E_i + wS*S_i + wI*I_i + wF*(M_i*Freedom_t) + wN*U_neighbors + wG*(1-Gini_t) + wSec*Security_t )`

Constraints:

- All weights sum to `1`.
- `Freedom_t` depends on governance mode and conformity pressure.
- Add small inertia term to prevent unstable oscillations.

### 4.3 Legitimacy Stock (New)

Introduce system-level legitimacy `L(t)`:

`L(t+1) = rho*L(t) + (1-rho)*g(mean(U), var(U), fairness, transparency, coercion)`

Impact:

- Low `L` lowers compliance, tax efficiency, and policy execution quality.
- Helps connect micro sentiment and macro institutional stability.

---

## 5) Metrics (Operationalized)

Track per tick and in rolling windows:

1. Freedom heterogeneity: `std(M)` + behavior entropy
2. Corruption loss rate: `(R_produced - R_actual) / R_produced`
3. Result fairness: Gini over `E`
4. Opportunity fairness: promotion gap under same `H` but different `S`
5. Mobility: rank correlation drift (`Spearman rho` over windows)
6. Happiness: mean/median/skew of `U`
7. Efficiency: `R/N` and growth slope
8. Resilience: half-life after shocks to recover 90% baseline `U`
9. Information symmetry: mean and variance of `I`
10. Legitimacy: `L(t)` trend and drawdown depth

---

## 6) Experimental Design

### 6.1 Baseline

- 1000 ticks per run
- Statistics from final 200 ticks
- At least 30 seeds per configuration

### 6.2 Sensitivity Analysis

Grid over:

- Initial inequality: low / medium / high
- Shock frequency: 1% / 5% / 10%
- AI objective: GDP / fairness / happiness / stability
- Oversight in human mode: 0.2 to 0.7
- Conformity pressure in AI mode: low to high

### 6.3 Mixed Regime

- Human (0-499) -> AI (500-999)
- Add transition cost: temporary drop in `L`, `U`, and execution quality
- Evaluate overshoot, damping time, and post-transition plateau

---

## 7) Hypotheses (Testable)

- H1: AI mode outperforms human mode on efficiency and result fairness under stable shocks, but lowers freedom heterogeneity.
- H2: Human mode can outperform AI mode on resilience under high-volatility shock environments due to adaptive flexibility.
- H3: There exists a switching interval where delayed transition reduces cumulative welfare loss.
- H4: AI fairness gains vanish if objective mismatch and lag exceed threshold values.

---

## 8) Minimal Engineering Plan

Suggested modules:

- `agent.py` (`Agent` dataclass + behavior functions)
- `governance.py` (`HumanGovernance`, `AIGovernance`)
- `model.py` (`SocietyModel`, tick orchestration)
- `metrics.py` (all indicators + rolling stats)
- `experiments.py` (batch runs, seed control, parameter sweeps)
- `plots.py` (time series, radar, violin, phase diagrams)
- `config.py` (all tunable parameters)
- `main.py` (CLI entry)

Output artifacts:

- CSV per run (tick-level metrics)
- JSON summary per experiment set
- PNG charts and a final comparative report

---

## 9) Validation and Reproducibility

- Deterministic random seeds and logged configs.
- Unit checks for metric bounds and conservation constraints.
- Sanity checks:
  - zero-shock scenario monotonicity
  - no-governance ablation
  - extreme-parameter stress tests

This design is intentionally competition-friendly: explicit assumptions, controlled comparison, measurable outputs, and robust sensitivity analysis.
