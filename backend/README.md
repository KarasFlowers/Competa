# Competa Backend

AI 竞品分析 Agent 协作系统 — 后端服务。

## 快速启动

```bash
# 1. 复制环境变量
cp .env.example .env
# 编辑 .env 填入 LLM_API_KEY

# 2. 安装依赖
uv sync

# 3. 启动服务
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API 文档：http://127.0.0.1:8000/docs

## 测试

```bash
uv run pytest
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_API_KEY` | OpenAI 兼容 API Key | （必填） |
| `LLM_BASE_URL` | API Base URL | `https://api.openai.com/v1` |
| `LLM_MODEL` | 模型名称 | `gpt-4o-mini` |
| `DATABASE_URL` | 数据库连接串 | `sqlite+aiosqlite:///./competa.db` |
| `DEBUG` | 调试模式 | `false` |