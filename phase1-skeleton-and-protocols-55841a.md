# 阶段一：项目骨架与基础协议

本阶段完成 Competa 项目的前后端初始化、核心 Schema 定义、基础 API 和数据库模型、Guardrails 校验层，为后续 Agent DAG 编排奠定数据和协议基础。

## 1. 产出目标

- 后端可启动，API 可访问（`/api/health` 返回 200）。
- 核心竞品知识 Schema（Pydantic）定义完毕，可通过 `pytest` 校验。
- 数据库可建表，任务/报告/溯源/Trace 的 CRUD API 可用。
- Guardrails 校验层可用：任意 Pydantic Schema 输入不合规时返回结构化错误。
- 前端可启动，展示占位页面（Landing + 任务创建表单骨架）。
- 本地开发环境一键启动说明完备。

## 2. 目录结构

```
Competa/                          # 项目根目录
├── backend/
│   ├── pyproject.toml            # uv 项目配置
│   ├── .env.example              # 环境变量模板
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI 入口 + lifespan
│   │   ├── config.py             # Settings（pydantic-settings）
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── router.py         # 汇总路由
│   │   │   ├── tasks.py          # 任务 CRUD
│   │   │   ├── reports.py        # 报告查询
│   │   │   └── traces.py         # Trace 查询
│   │   ├── schemas/
│   │   │   ├── __init__.py       # 统一导出
│   │   │   ├── base.py           # BaseModel、AgentMessage 及子类型、Source、Evidence、Claim
│   │   │   ├── competitive.py    # FeatureTree、PricingModel、Persona、SWOT
│   │   │   ├── report.py         # Report、ReportSection
│   │   │   ├── agent.py          # AgentRole、AgentRegistry
│   │   │   ├── ratchet.py        # QAIssue、ConstraintRule、TaskMetrics
│   │   │   └── trace.py          # TraceEvent、AgentTrace
│   │   ├── guardrails/
│   │   │   ├── __init__.py
│   │   │   └── validator.py      # Schema 校验 + 错误格式化
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── database.py       # SQLAlchemy ORM 模型
│   │   └── db/
│   │       ├── __init__.py
│   │       └── session.py        # engine + session 工厂
│   └── tests/
│       ├── __init__.py
│       ├── test_schemas.py        # Schema 校验测试
│       ├── test_guardrails.py     # Guardrails 测试
│       └── test_api.py           # API 基础测试
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       │   └── client.ts         # API 请求封装
│       ├── components/
│       │   └── Layout.tsx        # 基础布局
│       └── pages/
│           ├── Landing.tsx        # 首页
│           └── TaskCreate.tsx     # 任务创建骨架
├── docs/
│   └── architecture.md           # 架构说明
├── .gitignore                    # 已存在，需补充 backend/ 和 frontend/ 条目
├── .githooks/                    # 已存在，不动
├── CONTRIBUTING.md               # 已存在，不动
└── README.md                     # 项目总 README
```

## 3. 核心依赖

### 后端（pyproject.toml）

- `fastapi` + `uvicorn` — Web 框架 + ASGI 服务器
- `pydantic` >= 2.0 + `pydantic-settings` — Schema 定义 + 配置管理
- `sqlalchemy` >= 2.0 + `aiosqlite` — ORM + 异步 SQLite 驱动
- `httpx` — 异步 HTTP 客户端（后续 LLM 调用用）
- `pytest` + `pytest-asyncio` + `httpx` — 测试

### 前端（package.json）

- `react` + `react-dom` — UI 框架
- `typescript` — 类型安全
- `vite` — 构建工具
- `tailwindcss` + `@tailwindcss/vite` — 样式
- `lucide-react` — 图标
- `axios` — API 请求

## 4. 核心 Schema 定义

### 4.1 基础类型（base.py）

```
Source        — 数据来源（type: url|document|interview|survey, url?, title, content_snippet, fetched_at）
Evidence      — 证据条目（source_id, quote, relevance_score）
Claim         — 分析结论（content, evidence_ids: list[str], confidence: float, category）
AgentMessage  — Agent 间通信消息（from_agent, to_agent, message_type: collect_request|collect_result|analyze_request|analyze_result|write_request|write_result|qa_feedback, payload: 对应 message_type 的 Pydantic 子类型, timestamp）
  - CollectRequest  — 采集指令（task_id, target_products, source_types, focus_areas）
  - CollectResult   — 采集结果（sources: list[Source], coverage_note: str）
  - AnalyzeRequest  — 分析指令（task_id, sources: list[Source], analysis_dimensions: list[str]）
  - AnalyzeResult   — 分析结果（feature_trees, pricing_models, personas, swot_analyses）
  - WriteRequest    — 撰写指令（task_id, analysis: AnalyzeResult, report_style: str）
  - WriteResult     — 撰写结果（report: Report）
  - QAFeedback      — 质检反馈（passed: bool, issues: list[QAIssue], retry_target: str, constraints: list[ConstraintRule]）
```

### 4.2 竞品知识类型（competitive.py）

```
FeatureNode   — 功能树节点（name, description, status: supported|partial|missing, children: list[FeatureNode]）
FeatureTree   — 功能树（product_name, root_nodes: list[FeatureNode]）
PricingTier   — 定价档位（name, price, currency, period, features: list[str], limitations: list[str]）
PricingModel  — 定价模型（product_name, model_type: freemium|subscription|one_time|usage_based, tiers: list[PricingTier]）
Persona       — 用户画像（segment_name, demographics, pain_points, needs, product_usage_patterns）
SWOTItem      — 单条 SWOT 项（category: strength|weakness|opportunity|threat, content, evidence_ids）
SWOT          — SWOT 分析（product_name, items: list[SWOTItem]）
```

### 4.3 报告类型（report.py）

```
ReportSection — 报告章节（title, content: str, claims: list[Claim], subsections: list[ReportSection]）
Report        — 完整报告（task_id, title, executive_summary, sections: list[ReportSection], generated_at）
```

### 4.4 Agent 角色注册（agent.py）

```
AgentRole      — Agent 角色定义（name, role_type: collector|analyst|writer|qa, description, input_schema: str, output_schema: str, allowed_tools: list[str], max_retries: int）
AgentRegistry  — 角色注册表（roles: dict[str, AgentRole]，提供 lookup 和 validate 方法）
```

### 4.5 棘轮约束与 KPI（ratchet.py）

```
QAIssue           — 质检问题（issue_type: missing_field|missing_evidence|schema_violation|low_coverage, field_path: str, description, severity: critical|warning）
ConstraintRule    — 棘轮约束（rule_id, source_issue: QAIssue, constraint_type, constraint_value: str, applied_to: str, created_at）
TaskMetrics       — 任务指标（task_id, source_count, claim_count, evidence_coverage_rate: float, manual_correction_count: int, calculated_at）
```

### 4.6 Trace 类型（trace.py）

```
TraceEvent    — 单条追踪事件（agent_name, event_type: start|end|error|output, timestamp, input_summary?, output_summary?, token_count?, error_message?）
AgentTrace    — 单个 Agent 完整追踪（agent_name, task_id, events: list[TraceEvent], total_duration?, total_tokens?, status: running|completed|failed）
```

## 5. 数据库模型（SQLAlchemy）

| 表名 | 关键字段 | 说明 |
|------|---------|------|
| `tasks` | id, industry, target_product, competitors (JSON), status, created_at, updated_at | 分析任务 |
| `sources` | id, task_id, type, url, title, content_snippet, fetched_at | 数据来源 |
| `reports` | id, task_id, title, content (JSON), status, created_at | 竞品报告 |
| `traces` | id, task_id, agent_name, events (JSON), total_duration, total_tokens, status | Agent 追踪 |
| `constraints` | id, task_id, rule_id, source_issue (JSON), constraint_type, constraint_value, applied_to, created_at | 棘轮约束 |
| `metrics` | id, task_id, source_count, claim_count, evidence_coverage_rate, manual_correction_count, calculated_at | 业务 KPI |

MVP 阶段用 SQLite + JSON 字段存储结构化数据，避免过早引入关系型拆分。

## 6. API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| POST | `/api/tasks` | 创建分析任务 |
| GET | `/api/tasks` | 列出任务 |
| GET | `/api/tasks/{id}` | 查询单个任务 |
| GET | `/api/tasks/{id}/report` | 获取任务报告 |
| GET | `/api/tasks/{id}/sources` | 获取任务来源列表 |
| GET | `/api/tasks/{id}/traces` | 获取任务 Trace |

## 7. Guardrails 校验层

- `validate_output(schema_cls, data)` → 合格返回模型实例，不合格返回 `GuardrailError`（含字段路径、错误类型、修复建议）。
- 后续每个 Agent 的输出都经过此层校验，不合格时自动触发重试或打回。
- 阶段一只实现校验函数和错误格式，不接入 Agent 流程（阶段二接入）。

## 8. 实施步骤

1. **初始化后端**：`uv init backend`，配置 pyproject.toml，安装依赖。
2. **定义 Schema**：编写 `app/schemas/` 下所有 Pydantic 模型，编写 `test_schemas.py` 验证序列化/反序列化。
3. **建立数据库**：编写 SQLAlchemy 模型和 session 管理，实现自动建表。
4. **实现 API**：编写 FastAPI 路由，连接数据库模型，编写 `test_api.py`。
5. **实现 Guardrails**：编写 `validator.py`，编写 `test_guardrails.py`。
6. **初始化前端**：`npm create vite@latest frontend -- --template react-ts`，配置 TailwindCSS。
7. **前端骨架**：实现 Layout、Landing 页面、TaskCreate 表单骨架、API client。
8. **编写文档**：README.md（项目说明 + 一键启动）、architecture.md（架构概览）、.env.example。
9. **验证**：后端 `uv run pytest` 全通过，前端 `npm run dev` 可访问，`/api/health` 返回 200。

## 9. 验收检查

- [ ] `uv run pytest` 后端测试全通过
- [ ] `uv run uvicorn app.main:app` 启动无报错，`/api/health` 返回 200
- [ ] 所有 Schema 可通过 Pydantic 校验，序列化/反序列化正确
- [ ] Guardrails 校验层对合规数据通过、对不合规数据返回结构化错误
- [ ] 数据库自动建表，CRUD API 可用
- [ ] 前端 `npm run dev` 可访问，展示 Landing 和 TaskCreate 骨架
- [ ] README 包含一键启动说明
