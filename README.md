# Competa

Competa 是一个面向竞品分析场景的多 Agent 协作系统。它把“信息采集、调研设计、调研执行、证据筛选、结构化分析、报告撰写、QA 返工”串成一条可追踪的流水线，让输出不只是像报告，更像一套可复盘的研究过程。

## 这个项目解决什么问题

传统 AI 竞品分析很容易停在两种不够用的状态：

- 只会抓资料，但结论和证据脱节
- 能生成报告，但过程不可追踪、失败后要从头再来

Competa 想解决的是更接近真实工作流的问题：

- 让一手调研环节真正进入分析链路，而不是只做网页摘要
- 让每条关键结论都能回溯到来源
- 让 QA 失败后的返工有方向，而不是整条链路盲目重跑
- 让运行质量、人工修正和多轮改进都能被记录下来

## 核心能力

- `10 节点 DAG`：`Collector -> Survey -> Interview -> Fieldwork -> Curator -> Analyst -> Writer -> Screenshot -> Filter -> QA`
- `断点续跑`：基于 LangGraph SQLite checkpoint，失败后可以从中断点恢复，而不是整条链路重来
- `调研闭环`：问卷、访谈提纲、fieldwork 结果会回流为后续分析证据
- `证据筛选层`：来源去重、低质量剔除、单域名限额、保留/剔除原因持久化
- `Evidence 强约束`：无引用 Claim 会在 Filter 节点被过滤掉
- `QA + 棘轮约束`：失败模式会沉淀成约束，后续重跑时减少重复错误
- `质量评分 Eval`：对每次运行计算质量分，拆解证据覆盖、结构完整度、引用密度、来源质量
- `人工确认门`：分析完成后可暂停，用户补充写作约束后再继续生成报告
- `任务工作台`：集中查看任务状态、产物入口、运行历史、质量指标和人工修正情况
- `启动保护`：前端会等待后端健康检查就绪，避免启动早期误报“无法连接”

## 系统流程

```text
用户输入
  -> Collector
  -> Survey
  -> Interview
  -> Fieldwork
  -> Curator
  -> Analyst
  -> Writer
  -> Screenshot
  -> Filter
  -> QA

QA 失败:
  -> 定向打回 Collector / Analyst / Writer

人工确认模式:
  -> Analyst 完成后暂停
  -> 用户补充约束
  -> 从 Writer 继续
```

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 后端 | Python 3.11+, FastAPI, SQLAlchemy, Pydantic v2, LangGraph |
| 前端 | React 19, TypeScript, Vite, Tailwind CSS 4 |
| 存储 | SQLite |
| 模型接入 | OpenAI 兼容 API |
| 搜索 | `ddgs` / `tavily` 可切换 |

## 快速启动

### 前置条件

- Python `3.11+`
- Node.js `18+`
- `uv`（推荐，也可以用 `pip`）

### Windows 一键启动

```powershell
.\start-dev.ps1
```

脚本会自动：

- 检查并初始化 `backend/.venv`
- 安装前端依赖
- 启动后端 `http://127.0.0.1:8000`
- 启动前端 `http://127.0.0.1:5173`
- 自动打开浏览器

如果前端比后端先起来，应用会先等待 `/api/health`，不会直接把短暂启动过程显示成连接失败。

### 手动启动

```bash
# backend
cd backend
# 首次运行前，将 .env.example 复制为 .env 并填写所需配置
uv sync
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```bash
# frontend
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

启动后访问：

- 前端：<http://127.0.0.1:5173>
- 后端文档：<http://127.0.0.1:8000/docs>

## 环境变量

可以参考 [backend/.env.example](backend/.env.example)。

| 变量 | 说明 | 常见取值 |
| --- | --- | --- |
| `LLM_API_KEY` | 主 API Key | 必填，除非开启 mock |
| `LLM_API_KEY_2` / `LLM_API_KEY_3` | 备用 Key | 可选 |
| `LLM_BASE_URL` | OpenAI 兼容接口地址 | 如 `https://api.openai.com/v1` |
| `LLM_MODEL` | 模型名 | 如 `gpt-4o-mini` |
| `LLM_MOCK` | 是否启用 mock LLM | `true` / `false` |
| `DATABASE_URL` | 数据库连接串 | 默认 SQLite |
| `SEARCH_PROVIDER` | 搜索提供方 | `ddgs` / `tavily` / `none` |
| `TAVILY_API_KEY` | Tavily Key | 使用 Tavily 时必填 |
| `SEARCH_MAX_RESULTS` | 单次搜索最大结果数 | 如 `10` |
| `SEARCH_FETCH_CONTENT` | 是否抓取页面正文 | `true` / `false` |
| `RESPECT_ROBOTS_TXT` | 是否遵守 robots.txt | `true` / `false` |
| `DEBUG` | 调试模式 | `true` / `false` |

如果你只是想本地看交互和链路，可以把 `LLM_MOCK=true`，这对调 UI 和联调很方便。

## 前端使用路径

- `/`：项目首页
- `/tasks`：任务工作台
- `/tasks/new`：创建任务
- `/tasks/:id`：任务详情、运行控制、人工确认入口
- `/tasks/:id/report`：报告查看与引用回溯
- `/tasks/:id/traces`：执行追踪与 DAG 状态
- `/tasks/:id/survey`：问卷查看
- `/tasks/:id/interview`：访谈提纲查看
- `/demos/:scenarioId`：预置演示场景

## 后端 API 概览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/health` | 健康检查 |
| `POST` | `/api/tasks` | 创建任务 |
| `GET` | `/api/tasks/overview` | 获取工作台总览 |
| `POST` | `/api/tasks/{id}/run` | 启动任务 |
| `POST` | `/api/tasks/{id}/rerun` | 保留来源与约束重跑 |
| `POST` | `/api/tasks/{id}/continue` | 人工确认后继续执行 |
| `GET` | `/api/tasks/{id}/constraints` | 获取约束列表 |
| `GET` | `/api/tasks/{id}/runs` | 获取运行历史 |
| `GET` | `/api/tasks/{id}/runs/latest/compare` | 对比最近两次运行 |
| `GET` | `/api/tasks/{id}/dag` | 获取 DAG 结构与状态 |
| `GET` | `/api/tasks/{id}/report` | 获取报告 |
| `GET` | `/api/tasks/{id}/export` | 导出 Markdown / Word |
| `GET` | `/api/tasks/{id}/sources` | 获取来源列表 |
| `GET` | `/api/tasks/{id}/metrics` | 获取质量指标 |
| `GET` | `/api/tasks/{id}/traces` | 获取执行追踪 |
| `GET` | `/api/tasks/{id}/analysis` | 获取结构化分析产物 |
| `GET` | `/api/tasks/{id}/survey` | 获取问卷 |
| `GET` | `/api/tasks/{id}/interview` | 获取访谈提纲 |

完整接口说明以 FastAPI 文档为准：<http://127.0.0.1:8000/docs>

## 测试

后端测试：

```bash
cd backend
uv run pytest
```

前端构建校验：

```bash
cd frontend
npm run build
```

## 项目结构

```text
Competa/
├── backend/
│   ├── app/
│   │   ├── agents/          # 各角色 Agent
│   │   ├── api/             # REST API
│   │   ├── db/              # 数据库与轻量迁移
│   │   ├── guardrails/      # 报告与 schema 约束
│   │   ├── llm/             # 模型适配与 prompt
│   │   ├── models/          # ORM 模型
│   │   ├── orchestration/   # LangGraph DAG、state、runner
│   │   ├── schemas/         # Pydantic schema
│   │   └── services/        # 搜索、筛选、导出、截图、评分
│   └── tests/
├── frontend/
│   └── src/
│       ├── api/
│       ├── components/
│       └── pages/
├── reference/               # 本地参考项目，不参与主线开发
├── start-dev.ps1
└── start-dev.bat
```

## 适合继续升级的方向

- 更完整的运行观测面板，比如按节点拆分耗时、token、失败原因
- 更细粒度的人工介入，不只在写作前暂停
- PostgreSQL 持久化与多用户协作能力
- 更强的 Eval 基准和回归数据集

如果你是第一次接手这个项目，推荐的阅读顺序是：

1. 先看这个 README，明确链路和运行方式
2. 再看 [backend/app/orchestration/graph.py](backend/app/orchestration/graph.py)
3. 然后看 [backend/app/orchestration/runner.py](backend/app/orchestration/runner.py) 和 [backend/app/api/tasks.py](backend/app/api/tasks.py)
4. 最后再结合前端的 [frontend/src/pages/TaskCreate.tsx](frontend/src/pages/TaskCreate.tsx) 与 [frontend/src/pages/TaskDetail.tsx](frontend/src/pages/TaskDetail.tsx) 看用户路径
