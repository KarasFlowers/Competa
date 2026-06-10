# Competa — AI 竞品分析 Agent 协作系统

多 Agent 协作的数字调研小组：从信息采集到结构化报告，全链路自动化，每条结论可溯源。

## 系统架构

```
用户输入 → Collector → Survey → Interview → Fieldwork → Curator → Analyst → Writer → Screenshot → Filter → QA
                                                                                                          │
                ┌──────────────────────────────────────── QA 打回（最多 2 轮）──────────────────────────────┘
                └────────────────────────────── rerun 保留来源与约束，重新生成报告 ──────────────────────────┘
```

- **Collector**：多源信息采集（URL / 文档 / 访谈 / 问卷）
- **Survey / Interview / Fieldwork**：设计并回流调研证据，让一手研究真正进入分析链路
- **Curator**：去重、限域、筛除低质量来源，形成可解释的证据筛选结果
- **Analyst**：结构化分析（功能树 / 定价 / 用户画像 / SWOT）
- **Writer**：报告撰写（含引用标注）
- **Screenshot**：补充竞品网页截图证据
- **Filter**：过滤无引用 Claim（强制 Evidence 绑定）
- **QA**：质检 + 棘轮约束 + 结构化 Handoff 返工指令

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.11+ / FastAPI / SQLAlchemy / Pydantic v2 / LangGraph / OpenAI API |
| 前端 | React 19 / TypeScript / Vite / TailwindCSS 4 / Lucide Icons |
| 存储 | SQLite（MVP，可升级 PostgreSQL） |
| 编排 | LangGraph StateGraph + 条件边 |

## 一键启动

### 前置条件

- Python 3.11+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/)（推荐）或 pip

### 快速启动（Windows）

```powershell
.\start-dev.ps1
```

自动安装依赖、启动后端（:8000）和前端（:5173），并打开浏览器。

### 手动启动

```bash
# 后端
cd backend
cp .env.example .env          # 填入 LLM_API_KEY
uv sync                       # 或 pip install -e .
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 前端
cd frontend
npm install
npm run dev
```

访问 http://127.0.0.1:5173

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_API_KEY` | OpenAI 兼容 API Key | （必填） |
| `LLM_BASE_URL` | API Base URL | `https://api.openai.com/v1` |
| `LLM_MODEL` | 模型名称 | `gpt-4o-mini` |
| `DATABASE_URL` | 数据库连接串 | `sqlite+aiosqlite:///./competa.db` |
| `DEBUG` | 调试模式 | `false` |

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| POST | `/api/tasks` | 创建分析任务 |
| GET | `/api/tasks/overview` | 获取任务工作台总览与产物状态 |
| GET | `/api/tasks` | 列出任务 |
| GET | `/api/tasks/{id}` | 查询任务 |
| POST | `/api/tasks/{id}/run` | 启动 Pipeline |
| POST | `/api/tasks/{id}/rerun` | 保留来源与约束重新生成 |
| GET | `/api/tasks/{id}/status` | 查询执行状态 |
| GET | `/api/tasks/{id}/constraints` | 获取约束规则 |
| GET | `/api/tasks/{id}/runs` | 获取运行历史 |
| GET | `/api/tasks/{id}/runs/latest/compare` | 对比最近两次运行 |
| GET | `/api/tasks/{id}/dag` | 获取 DAG 结构与节点状态 |
| GET | `/api/tasks/{id}/report` | 获取报告 |
| GET | `/api/tasks/{id}/export` | 导出 Markdown / Word |
| GET | `/api/tasks/{id}/sources` | 获取来源列表 |
| GET | `/api/tasks/{id}/sources/{sid}` | 获取单个来源详情 |
| GET | `/api/tasks/{id}/metrics` | 获取质量指标 |
| GET | `/api/tasks/{id}/traces` | 获取执行追踪 |
| GET | `/api/tasks/{id}/analysis` | 获取结构化分析产物 |
| GET | `/api/tasks/{id}/survey` | 获取问卷设计 |
| GET | `/api/tasks/{id}/interview` | 获取访谈提纲 |

完整 API 文档：http://127.0.0.1:8000/docs

## 前端页面

| 路由 | 页面 |
|------|------|
| `/` | 首页（功能介绍） |
| `/demos/:scenarioId` | 预置示例场景 |
| `/tasks` | 任务工作台（筛选、追踪、快捷访问产物） |
| `/tasks/new` | 创建分析任务 |
| `/tasks/:id` | 任务详情 + 运行控制 + 证据筛选摘要 |
| `/tasks/:id/report` | 报告查看 + 引用溯源 + 来源筛选解释 |
| `/tasks/:id/traces` | 执行追踪与 DAG 回放 |
| `/tasks/:id/survey` | 问卷查看 |
| `/tasks/:id/interview` | 访谈提纲查看 |

## 核心特性

- **棘轮机制**：QA 失败模式自动转化为 ConstraintRule，后续 Agent 不会重复同类错误
- **Evidence 强制绑定**：无引用 Claim 被 Filter 节点过滤，不进入最终报告
- **证据筛选层**：来源会被去重、质量筛选、域名限额，并对保留/剔除原因做持久化
- **结构化 Handoff**：QA 打回通过 HandoffInstruction 传递目标 Agent、问题类型、失败字段、证据要求
- **改善记录**：重跑后 evidence_coverage delta 写入 Trace，可量化展示改进
- **运行历史对比**：最近两次运行可直接比较分析证据数、覆盖率、重试次数与人工修正情况
- **任务工作台**：集中查看任务状态、报告就绪情况、核心质量指标与调研产物入口
- **前端按需加载**：路由与重型可视化组件按需加载，降低首屏包体，提升演示流畅度

## 测试

```bash
cd backend
uv run pytest
```

## 项目结构

```
Competa/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── agents/          # Collector / Survey / Interview / Fieldwork / Analyst / Writer / QA
│   │   ├── api/             # REST API 端点
│   │   ├── db/              # 数据库 session 管理
│   │   ├── guardrails/      # Schema 校验层
│   │   ├── llm/             # LLM 适配器 + Prompt 模板
│   │   ├── models/          # SQLAlchemy ORM 模型
│   │   ├── orchestration/   # LangGraph DAG + State + Runner
│   │   ├── services/        # curation / export / screenshot 等服务层
│   │   └── schemas/        # Pydantic Schema 定义
│   └── tests/               # pytest 测试
├── frontend/                # React 前端
│   └── src/
│       ├── api/             # API client
│       ├── components/      # Layout 等公共组件
│       └── pages/           # 页面组件（已按路由懒加载）
└── reference/               # 参考项目（.gitignore）
```
