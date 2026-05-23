# Competa 系统架构

## 整体架构

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────────────────────┐
│   前端       │────▶│   后端 API    │────▶│   LangGraph DAG 编排            │
│   React SPA  │     │   FastAPI     │     │                                 │
│              │     │              │     │   ┌─────────┐  ┌─────────┐    │
│  - 任务表单   │     │  - REST API  │     │   │Collector│─▶│Analyst  │    │
│  - 报告查看   │     │  - SSE 推送  │     │   └─────────┘  └─────────┘    │
│  - 溯源跳转   │     │  - CRUD      │     │        │            │          │
│  - 决策回放   │     │              │     │        ▼            ▼          │
│              │     │              │     │   ┌─────────┐  ┌─────────┐    │
│              │     │              │     │   │  QA     │◀─│ Writer  │    │
│              │     │              │     │   └─────────┘  └─────────┘    │
│              │     │              │     │        │ (打回)               │
│              │     │              │     │        └──────▶ Collector/    │
│              │     │              │     │                Analyst/Writer │
└─────────────┘     └──────────────┘     └─────────────────────────────────┘
                           │
                     ┌─────┴──────┐
                     │   SQLite    │
                     │            │
                     │ - tasks    │
                     │ - sources  │
                     │ - reports  │
                     │ - traces   │
                     │ - constraints│
                     │ - metrics  │
                     └────────────┘
```

## 后端模块

### API 层 (`app/api/`)

- `router.py` — 汇总路由 + `/api/health`
- `tasks.py` — 任务 CRUD (`POST /api/tasks`, `GET /api/tasks`, `GET /api/tasks/{id}`)
- `reports.py` — 报告查询 (`GET /api/tasks/{id}/report`, `GET /api/tasks/{id}/sources`)
- `traces.py` — Trace 查询 (`GET /api/tasks/{id}/traces`)

### Schema 层 (`app/schemas/`)

核心 Pydantic 模型，定义 Agent 间通信协议：

| 文件 | 核心类型 | 说明 |
|------|---------|------|
| `base.py` | Source, Evidence, Claim, AgentMessage | 基础数据单元 + Agent 间消息 |
| `competitive.py` | FeatureTree, PricingModel, Persona, SWOT | 竞品知识结构 |
| `report.py` | Report, ReportSection | 结构化报告 |
| `agent.py` | AgentRole, AgentRegistry | Agent 角色注册 |
| `ratchet.py` | QAIssue, ConstraintRule, TaskMetrics | 棘轮约束 + 业务 KPI |
| `trace.py` | TraceEvent, AgentTrace | 可观测性追踪 |

### AgentMessage 协议

Agent 间通信使用 `AgentMessage`，payload 为 discriminated union：

```
AgentMessage
├── message_type: collect_request → CollectRequest
├── message_type: collect_result → CollectResult
├── message_type: analyze_request → AnalyzeRequest
├── message_type: analyze_result → AnalyzeResult
├── message_type: write_request → WriteRequest
├── message_type: write_result → WriteResult
└── message_type: qa_feedback → QAFeedback
```

### Guardrails 层 (`app/guardrails/`)

- `validate_output(schema_cls, data)` — 校验 Agent 输出是否符合 Schema
- 合格返回模型实例，不合格抛出 `GuardrailError`（含字段路径、错误类型、修复建议）
- 每个 Agent 的输出都经过此层校验

### 数据库层 (`app/models/`, `app/db/`)

- SQLAlchemy 2.0 异步 ORM + aiosqlite
- 6 张表：tasks, sources, reports, traces, constraints, metrics
- 结构化数据用 JSON 字段存储，避免过早关系型拆分

## DAG 编排流程

```
Start → Collect → Analyze → Write → QA → End
                                    │
                                    ├── passed=true → End
                                    └── passed=false → 回退到
                                        Collect / Analyze / Writer
                                        (携带 ConstraintRule 棘轮约束)
```

### 棘轮机制

QA 打回时：
1. 生成 `QAIssue`（问题类型、字段路径、严重程度）
2. 将 `QAIssue` 转化为 `ConstraintRule`（约束类型、约束值、目标 Agent）
3. 后续 Agent 执行时携带所有累积的 `ConstraintRule`
4. 确保同类错误不会重复发生

## 前端架构

- React 19 + TypeScript + Vite
- TailwindCSS v4 样式
- react-router-dom 路由
- axios API 请求（Vite proxy 到后端）

### 页面

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | Landing | 首页，功能介绍 |
| `/tasks/new` | TaskCreate | 新建分析任务 |
| `/tasks` | TaskList | 任务列表 |
| `/tasks/:id` | TaskDetail | 任务详情 + 报告 + 溯源 + Trace |
