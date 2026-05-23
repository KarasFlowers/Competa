# Competa — AI 驱动的竞品分析 Agent 协作系统

多 Agent 协作的数字调研小组，从信息采集到结构化报告，全链路自动化。

## 系统架构

```
用户 → 前端 (React) → 后端 (FastAPI) → LangGraph DAG
                                        ├── Collector Agent (信息采集)
                                        ├── Analyst Agent (结构化分析)
                                        ├── Writer Agent (报告撰写)
                                        └── QA Agent (质检 + 棘轮约束)
```

- **信息采集 Agent**：多源信息自动采集，覆盖公开网页、文档、问卷与访谈
- **分析师 Agent**：提取功能树、定价模型、用户画像、SWOT
- **报告撰写 Agent**：生成带引用来源的结构化竞品分析报告
- **质检 Agent**：校验完整性/引用/Schema 合规，不合格时打回重做（棘轮机制）

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.11+ / FastAPI / SQLAlchemy / aiosqlite |
| Agent 编排 | LangGraph (StateGraph + 条件边) |
| 结构化输出 | Pydantic v2 Schema + Guardrails 校验层 |
| 前端 | React 19 / TypeScript / Vite / TailwindCSS |
| 存储 | SQLite (MVP) |

## 快速启动

### 前置条件

- Python 3.11+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python 包管理)

### 后端

```bash
cd backend
cp .env.example .env    # 填入 LLM API 配置
uv sync
uv run uvicorn app.main:app --reload
# 访问 http://127.0.0.1:8000/docs 查看 API 文档
```

### 前端

```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
```

### 运行测试

```bash
cd backend
uv run pytest -v
```

## 项目结构

```
Competa/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI 路由 (tasks, reports, traces)
│   │   ├── schemas/      # Pydantic Schema 定义
│   │   ├── models/       # SQLAlchemy ORM 模型
│   │   ├── db/           # 数据库 session 管理
│   │   └── guardrails/   # Schema 校验层
│   └── tests/            # pytest 测试
├── frontend/
│   └── src/
│       ├── api/          # API 请求封装
│       ├── components/   # 通用组件
│       └── pages/        # 页面组件
├── docs/                 # 架构与协议文档
└── reference/            # 参考项目资料
```

## 核心特性

- **DAG 编排**：LangGraph StateGraph 定义 Collect → Analyze → Write → QA 流程，QA 不通过时条件回退
- **棘轮机制**：QA 打回时自动将失败模式转化为约束规则，确保错误不重复
- **信息溯源**：每条分析结论绑定 Evidence，可定位到原始数据源
- **Guardrails 校验**：Agent 输出必须通过 Pydantic Schema 校验才可进入下一节点
- **可观测性**：记录每个 Agent 的输入、输出、Prompt、耗时、Token 消耗

## 开发规范

参见 [CONTRIBUTING.md](./CONTRIBUTING.md) — Conventional Commits + 功能分支工作流。
