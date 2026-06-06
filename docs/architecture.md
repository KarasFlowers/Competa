# Competa 系统架构

## 1. 系统总览

Competa 是一个多 Agent 协作的 AI 竞品分析系统，核心流程为"信息采集 → 结构化分析 → 报告撰写 → 质检反馈 → 报告输出"，具备真实反馈闭环和信息溯源能力。

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend                         │
│                                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   │
│  │ Collector │──▶│ Analyst  │──▶│  Writer  │──▶│  Filter  │   │
│  │  Agent    │   │  Agent   │   │  Agent   │   │   Node   │   │
│  └──────────┘   └──────────┘   └──────────┘   └────┬─────┘   │
│       ▲                                             │          │
│       │              ┌──────────┐                   ▼          │
│       └──────────────│    QA    │◀────────────┌──────────┐   │
│        (retry ≤ 2)   │  Agent   │─────────────│  END /   │   │
│                      └──────────┘  passed?    │  Failed  │   │
│                           │                   └──────────┘   │
│                           ▼                                   │
│                    qa_router                                  │
│                    (conditional)                              │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    PipelineState                         │   │
│  │  task_id, task, sources, analysis, report, qa_feedback,  │   │
│  │  metrics, previous_metrics, handoff, traces, status,     │   │
│  │  error, retry_count, constraints                         │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       SQLite Database                           │
│  tasks │ sources │ reports │ traces │ constraints │ metrics     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      React Frontend                             │
│  Landing │ TaskCreate │ TaskDetail │ ReportView (+ Source 溯源) │
└─────────────────────────────────────────────────────────────────┘
```

## 2. Agent 职责

| Agent | 输入 | 输出 | 职责 |
|-------|------|------|------|
| **Collector** | target_product, competitors, industry, constraints | sources[] | 多源信息采集（URL/文档/访谈/问卷），采集前遵守 robots.txt |
| **Survey** | target_product, competitors, industry, focus_areas | survey（问卷题目） | 设计竞品分析问卷 |
| **Interview** | target_product, competitors, survey_questions | interview（访谈提纲） | 设计半结构化访谈提纲，承接问卷维度 |
| **Fieldwork** | survey, interview, personas | fieldwork + sources[] | 模拟执行问卷与访谈，结果回流为可溯源 SURVEY/INTERVIEW 证据 |
| **Analyst** | sources[], constraints | feature_trees, pricing_models, personas, swot_analyses | 结构化竞争情报提取 |
| **Writer** | analysis, target_product, constraints | report (sections + claims + evidence_ids) | 报告撰写，每条 Claim 绑定 Evidence |
| **QA** | report, sources, retry_count | passed, issues, metrics, handoff, constraints | 质检 + 棘轮约束生成 + Handoff 指令 |

> **调研执行闭环**：Survey/Interview Agent 只产出"设计"，Fieldwork Agent 基于 personas 与竞品上下文模拟生成问卷应答与访谈摘录（明确标注 `[模拟]`，reliability 0.55/0.6），并转成 SURVEY/INTERVIEW 类型 source 合入证据池喂给 Analyst——让"问卷调研、用户访谈"对最终结论真正产生贡献，而非悬空的设计产物。

## 3. DAG 编排（LangGraph）

流程定义在 `orchestration/graph.py`，使用 `StateGraph(PipelineState)` 构建：

```
collect → survey → interview → fieldwork → analyze → write → screenshot → filter → qa → qa_router
                                                                                        ├── passed → END
                                                                                        ├── retry_count > MAX_RETRIES → END (failed)
                                                                                        ├── retry_target == collector → collect
                                                                                        ├── retry_target == analyst → analyze
                                                                                        └── retry_target == writer → write
```

- **MAX_RETRIES = 2**：最多打回 2 次
- **qa_router**：确定性路由，由代码控制，LLM 只负责内容生成
- **filter_node**：过滤无 evidence_ids 的 Claim

## 4. 棘轮机制

QA 识别问题后，通过 `constraint_resolver.py` 将失败模式转化为约束规则：

1. QA 输出 issues → `determine_retry_target(issues)` 判定回退阶段
2. `issues_to_constraints(issues)` 生成 CONSTRAINT 字符串
3. `build_handoff(issues, retry_count)` 构建 HandoffInstruction
4. 约束注入重跑 Agent 的 user prompt 末尾
5. 约束持久化到 `constraints` 表

**效果**：同类错误不会重复发生（现有参考框架均未提供此能力）。

## 5. Schema 协议

所有 Agent 间通信通过 Pydantic Schema 约束：

```
schemas/
├── base.py          # Source, Evidence, Claim, AgentMessage, CollectResult, AnalyzeResult, QAFeedback
├── competitive.py   # FeatureTree, PricingModel, Persona, SWOT
├── report.py        # Report, ReportSection
├── agent.py         # AgentRole, AgentRegistry
├── ratchet.py       # QAIssue, ConstraintRule, TaskMetrics
├── handoff.py       # HandoffInstruction
└── trace.py         # TraceEvent, AgentTrace
```

每个 Agent 的 LLM 输出必须通过 `validate_output(schema, data)` 校验（Guardrails 层），不合格时自动重试（最多 3 次）。

## 6. Guardrails 校验层

位于 `guardrails/validator.py`：

- `validate_output(schema_cls, data)` → 合格返回模型实例，不合格抛出 `GuardrailError`
- `GuardrailError` 包含结构化字段错误：`field_path`、`error_type`、`message`、`suggestion`
- Agent 重试时将错误信息反馈给 LLM，引导其修正输出

## 7. LLM 适配层

位于 `llm/client.py`：

- 统一 OpenAI 兼容接口，通过 `LLM_BASE_URL` 适配不同供应商
- Token 预算机制：超出时自动裁剪低优先级内容
- JSON mode 强制结构化输出
- 重试机制在 `BaseAgent.call_and_validate` 中实现

## 8. 数据库模型

SQLite + SQLAlchemy async，6 张表：

| 表 | 说明 |
|----|------|
| `tasks` | 分析任务（目标产品、竞品、状态） |
| `sources` | 数据来源（URL/文档/访谈/问卷） |
| `analyses` | 结构化竞品知识（功能树/定价/画像/SWOT），驱动对比矩阵与 SWOT 象限 |
| `reports` | 结构化报告（JSON content） |
| `traces` | Agent 执行追踪（JSON events） |
| `constraints` | 棘轮约束记录 |
| `metrics` | 业务 KPI（覆盖率、引用率等） |

> **分析产物落地**：Analyst Agent 产出的 `AnalyzeResult`（功能树/定价模型/用户画像/SWOT）由 `runner.py` 持久化到 `analyses` 表，并通过 `GET /tasks/{id}/analysis` 暴露。前端 `ComparisonMatrix` 组件据此渲染**功能对比矩阵**（竞品为列、功能为行，✓/部分/✗ 状态色块）、**定价对比**、**SWOT 四象限**（条目带 evidence 角标可溯源）与**用户画像卡片**——区别于 Writer 产出的叙述性报告。

## 9. API 设计

RESTful API，前缀 `/api`：

- 任务 CRUD + 运行控制（`POST /tasks/{id}/run`）
- 报告/来源/指标/追踪查询
- 状态轮询（`GET /tasks/{id}/status`）

## 10. 前端架构

React SPA，Vite 构建，TailwindCSS 样式：

- `Layout` 组件提供导航栏
- 4 个页面：Landing / TaskCreate / TaskDetail / ReportView
- ReportView 支持引用标注点击 → Source 弹窗溯源
- TaskDetail 支持状态轮询 + Metrics 展示

## 11. Reference 借鉴点

| 参考项目 | 借鉴点 | 本项目差异化 |
|----------|--------|-------------|
| LangGraph | StateGraph + 条件边 + checkpoint | 垂直竞品分析 DAG + 棘轮约束 |
| CrewAI | 角色化 Agent + output_pydantic | 强制溯源 + QA 打回闭环 |
| OpenAI Agents SDK | handoff + guardrails + tracing | 结构化 HandoffInstruction + 改善记录 |
| Conductor | 确定性路由 + Dashboard | 不让 LLM 决定流程分支 |
| GPT-Researcher | 多源搜索 + 引用管理 | 竞品分析垂直场景 + Schema 约束 |
