# Backend

这个目录只放 Competa 的后端服务代码与测试。

如果你想先理解整个项目，请先看仓库根目录的 [README.md](../README.md)。这里保留的是后端维护者更需要的内容：如何启动服务、跑测试、看关键入口。

## 目录职责

```text
backend/
├── app/
│   ├── agents/          # 各角色 Agent
│   ├── api/             # FastAPI 路由
│   ├── db/              # 数据库 session 与轻量迁移
│   ├── guardrails/      # 报告与 schema 校验
│   ├── llm/             # 模型适配与 prompt
│   ├── models/          # ORM 模型
│   ├── orchestration/   # LangGraph DAG、state、runner
│   ├── schemas/         # Pydantic schema
│   └── services/        # 搜索、筛选、导出、截图、评分
├── scripts/
├── tests/
├── pyproject.toml
└── uv.lock
```

## 本地启动

```bash
cd backend
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

启动后可访问：

- API: <http://127.0.0.1:8000>
- Docs: <http://127.0.0.1:8000/docs>

## 测试

```bash
cd backend
uv run pytest
```

## 常用入口

- `app/main.py`：FastAPI 应用入口
- `app/api/tasks.py`：任务 API、运行控制、历史与约束接口
- `app/orchestration/graph.py`：DAG 定义
- `app/orchestration/runner.py`：运行器、checkpoint、状态持久化
- `app/services/curation.py`：证据筛选逻辑
- `app/services/evaluation.py`：运行质量评分

## 环境变量

以 [`.env.example`](./.env.example) 为准，最常用的是这些：

| 变量 | 说明 |
| --- | --- |
| `LLM_API_KEY` | 主模型 API Key |
| `LLM_API_KEY_2` / `LLM_API_KEY_3` | 备用 Key |
| `LLM_BASE_URL` | OpenAI 兼容接口地址 |
| `LLM_MODEL` | 模型名 |
| `LLM_MOCK` | 是否启用 mock 模型 |
| `DATABASE_URL` | 数据库连接串 |
| `SEARCH_PROVIDER` | `ddgs` / `tavily` / `none` |
| `TAVILY_API_KEY` | Tavily Key |
| `RESPECT_ROBOTS_TXT` | 是否遵守 robots.txt |
