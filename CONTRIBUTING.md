# 开发者贡献规范

## 1. 提交信息规范（Conventional Commits）

所有提交信息必须遵循以下格式：

```
<type>(<scope>): <subject>

<body>（可选）

<footer>（可选）
```

### Type 限定

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | 修复 Bug |
| `docs` | 仅文档变更 |
| `style` | 代码格式调整（不影响逻辑） |
| `refactor` | 重构（非 feat 也非 fix） |
| `test` | 添加或修改测试 |
| `chore` | 构建/工具/依赖等杂项 |

### 示例

- `feat(auth): add login page`
- `fix(api): resolve null pointer in user service`
- `docs(readme): update installation guide`
- `chore(hooks): add commit-msg validation`

## 2. 分支管理规范

### 分支模型

- **`main`**：受保护的主分支，代表稳定可发布版本
- **`feature/<描述>`**：新功能开发分支
- **`fix/<描述>`**：Bug 修复分支
- **`docs/<描述>`**：文档更新分支
- **`refactor/<描述>`**：重构分支

### 规则

1. **禁止直接提交到 `main` 分支**。所有变更必须通过功能分支提交。
2. 分支命名使用小写英文字母与连字符，例如：`feature/user-login`、`fix/api-timeout`。
3. 开发完成后，将功能分支合并回 `main`（建议先 rebase 再 merge，保持线性历史）。
4. 合并前确保本地测试通过。

## 3. 工作流建议

```bash
# 1. 从 main 拉取最新代码
git checkout main
git pull origin main

# 2. 创建功能分支
git checkout -b feature/my-feature

# 3. 开发并提交
git add .
git commit -m "feat(module): add new feature"

# 4. 推送分支到远程
git push -u origin feature/my-feature

# 5. 通过 Pull Request 合并到 main（后续操作）
```

## 4. 自动化约束

本项目已配置 Git Hooks：

- **`commit-msg`**：自动校验提交信息是否符合 Conventional Commits 格式，不符合将阻止提交。
- **`pre-commit`**：若当前分支为 `main`，将阻止直接提交并提示创建功能分支。

如需跳过 hooks（仅限紧急情况），可使用 `git commit --no-verify`，但不建议常规使用。
