
## 审计链（随附可查）

8 个历史探索点的完整审计链**随本仓库附送**，评委可逐条点开核验：

- `evidence/agent_trajectory/results/` — 8 个 Agent 选点的原始 `result.json`（thread depth / pitch / shell 0-2mm / S/V / 质量字段）
- `evidence/agent_trajectory/explore_log_*.json` — 两次探索会话的完整日志（当时知道什么、为何选点、预测什么）
- `evidence/pipeline_source/` — 探索管线源码（agent.py / env.py / run_simulation.py / generate_stl.py）
- `evidence/` 其余 — 盲测审计、骨嵴校准、契约、测度验证等关键证据

> Demo 首页「真实证据 → Agent 介入轨迹」的 8 个可点击点位，与上述 `result.json` 一一对应，可在线上核验。