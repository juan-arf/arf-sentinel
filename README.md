# ARF Sentinel

**The execution control plane for enterprise AI agents.**

> *Agents propose. ARF decides. The agent cannot grant itself authority.*

---

## The Problem

An agent identifies a critical CVE in `urllib3` affecting 147 repos and recommends an immediate upgrade. Technically correct — operationally dangerous.

**Who guards the guard?**

---

## The Solution

Three systems, one governance plane:

```bash
CRAFT (cyan) → NEMOTRON (violet) → ARF (green) → EXECUTION (red)
Discover Reason Authorize Enforce
```


| System | Role |
|--------|------|
| **CRAFT** | Enterprise dependency investigation |
| **Nemotron** | Agent reasoning & remediation planning |
| **ARF** | Independent Bayesian governance |

ARF evaluates **blast radius**, **evidence confidence**, and **policy constraints**, then decides: **APPROVE**, **DENY**, or **ESCALATE**.

---

## Demo Flow (auto‑playing)

| Phase | What happens |
|-------|-------------|
| 0 | Animated workflow. 147 repos, 63% blast radius |
| 1 | Live scanning bar: 89 direct, 58 transitive deps |
| 2 | Agent proposes upgrade with 92% confidence |
| 3 | Battle bar: ARF risk (82%) overtakes confidence |
| 4 | Bayesian formula. Expected loss chart. **ESCALATE** |
| 5 | Hard block: "Agent execution authority denied" |
| 6 | Counterfactual: 147→32 repos. Risk drops to 37% |
| 7 | Agent replans the canary upgrade |
| 8 | ARF **APPROVES**. Download audit PDF |

---

## Bayesian Governance

$$R = 0.5 + 0.5 \cdot B \qquad P(R|E) = \frac{P(E|R) \cdot P(R)}{P(E)}$$

ARF picks the action with **minimum expected loss**.

---

## Counterfactual Engine

When ARF escalates, it doesn't just block — it computes the **maximum safe scope** and guides the agent toward an approvable plan.

---

## Tech Stack

`Streamlit` `LangGraph` `Nebius Nemotron` `CRAFT MCP` `Plotly` `Pydantic` `fpdf2` `pytest`

---

## Quick Start

```bash
git clone https://github.com/juan-arf/arf-sentinel.git
cd arf-sentinel
pip install -r requirements.txt
streamlit run apps/arf_sentinel/app.py
```

> _"What happens when the agent is right, but the action is too dangerous? ARF finds the maximum safe action an agent can take."_

_Built for the Enterprise Agents Hackathon by Emergence AI & Nebius._
