# 🚨 OpenEnv: SRE Incident Simulator

An OpenEnv-compliant reinforcement learning environment that simulates real-world Site Reliability Engineering (SRE) and DevOps incidents.

---

## 🔥 Motivation

While many AI agents are evaluated on games or web-browsing tasks, there is a massive industry gap for evaluating agents on highly technical, terminal-driven infrastructure tasks.

This environment tests an LLM's ability to act as an **on-call engineer**:

* Investigating logs
* Inspecting configurations
* Deploying fixes
* Resolving microservice outages

---

## 🧩 Observation and Action Spaces

This environment strictly enforces structured outputs using **Pydantic models**.

### 📡 Observation Space

At every step, the agent receives an `SREObservation`:

```python
class SREObservation(BaseModel):
    ticket_description: str
    last_command_output: str
    services_available: list[str]
    step_count: int
```

* **ticket_description** → PagerDuty alert (constant)
* **last_command_output** → Terminal/log output from previous step
* **services_available** → Available services in the system
* **step_count** → Tracks SLA / steps taken

---

### ⚙️ Action Space

The agent must respond with an `SREAction`:

```python
class SREAction(BaseModel):
    command: Literal["query_logs", "inspect_config", "submit_resolution"]
    target: str
    proposed_fix: Optional[str] = None
```

* **command** → One of the allowed operations
* **target** → Service or config file
* **proposed_fix** → Only required for resolution

---

## 🎯 Reward Function (Partial Progress)

The environment returns an `SREReward` (range: `0.0 → 1.0`).

* ✅ `+0.2` → Correct log identified
* ✅ `+0.2` → Correct misconfiguration identified
* 🏆 `1.0` → Successful resolution before SLA (10 steps)

---

## 📋 Tasks & Difficulty Progression

| Task ID         | Difficulty | Description                   | Core Challenge                            |
| --------------- | ---------- | ----------------------------- | ----------------------------------------- |
| `task_1_easy`   | Easy       | Missing Environment Variable  | Identify missing JWT secret in logs       |
| `task_2_medium` | Medium     | DB Connection Pool Exhaustion | Trace timeout to DB config issue          |
| `task_3_hard`   | Hard       | Cascading SSL Failure         | Diagnose expired TLS cert across services |

---

## 🚀 Setup & Usage

### 🐳 Docker Execution (Recommended)

```bash
docker build -t sre-openenv .
docker run -p 7860:7860 sre-openenv
```

---

## 🧪 Baseline Inference Results

Example run using **Qwen 3.6 Plus via OpenRouter**:

```text
[START] task=task_1_easy | env=sre-incident-simulator | model=qwen/qwen3.6-plus:free

[STEP] step=1
  action={"command":"query_logs","target":"auth_service","proposed_fix":null}
  reward=0.20 | done=False

[STEP] step=2
  action={"command":"inspect_config","target":"auth_service","proposed_fix":null}
  reward=-0.05 | done=False

[STEP] step=3
  action={"command":"submit_resolution","target":"auth_service",
  "proposed_fix":"Set the missing 'JWT_SECRET' environment variable."}
  reward=1.00 | done=True

[END] success=True | steps=3 | score=1.00
```

---

## 🧠 Key Capabilities Evaluated

* Root cause analysis
* Log interpretation
* Config debugging
* Multi-service reasoning
* Decision-making under constraints

---

## 📦 Future Improvements

* More realistic Kubernetes simulation
* Stateful services and failures
* Chaos engineering scenarios
* Multi-agent collaboration mode

---

## 🏁 Summary

OpenEnv SRE Incident Simulator provides a **realistic benchmark** for evaluating LLMs in DevOps environments — moving beyond toy problems into **production-like incident response workflows**.

---

## ⭐ Contributing

Pull requests are welcome! Feel free to open issues for suggestions or improvements.

---

## 📄 License

MIT License
