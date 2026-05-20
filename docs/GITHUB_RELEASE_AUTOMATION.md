# GitHub Release 自动化说明

## 1. 已配置好的内容

仓库已经新增 GitHub Actions 发布工作流：

- 文件：`.github/workflows/release.yml`
- 触发方式：
  - 推送语义化版本 tag，例如：`v0.1.1`
  - 手动在 GitHub Actions 页面点击 `Run workflow`

这个工作流会自动完成：

1. 运行单元测试
2. 检查关键入口是否可编译
3. 构建 `.app`
4. 构建 `.dmg`
5. 构建 Python 包：`wheel` + `sdist`
6. 生成 `SHA256SUMS.txt`
7. 创建 GitHub Release
8. 上传 release 附件
9. 按需发布到 PyPI（前提是你已经配置好 PyPI Trusted Publisher，并开启仓库变量）

说明：

- GitHub Release 会上传 `.zip`、`.dmg`、`.whl`、`.tar.gz`
- 但 PyPI 只接受 Python 分发包，所以发布到 PyPI 时必须只传 `wheel` 和 `sdist`
- 当前工作流已单独整理 `pypi-dist/`，避免把 `.dmg`、`.zip` 误传给 PyPI

## 2. 以后怎么发 GitHub Release

每次发布建议这样做：

1. 更新 `pyproject.toml` 中的版本号
2. 更新 `CHANGELOG.md`
3. 提交代码并推送到 `main`
4. 打 tag
5. 推送 tag

示例：

```bash
git add .
git commit -m "chore: release v0.1.1"
git push origin main

git tag v0.1.1
git push origin v0.1.1
```

推送后，GitHub Actions 会自动：

- 构建 mac 发布产物
- 创建同名 Release
- 上传 `.zip`、`.dmg`、`.whl`、`.tar.gz`、`SHA256SUMS.txt`

## 3. PyPI 为什么可能第一次还不能自动发

GitHub Actions 这边已经准备好了发布步骤，但 PyPI 端还需要你手动做一次信任配置。

这是 PyPI 官方推荐的 Trusted Publisher 方式，不需要长期保存 API Token，安全性更高。

## 4. PyPI 需要手动配置的一次性步骤

登录 PyPI 后，进入你项目的发布配置页面，添加一个 Trusted Publisher。

建议填写：

- Owner: `github653224`
- Repository name: `DeepSeekBalanceMonitorForMac`
- Workflow name: `release.yml`
- Environment name: `pypi`

项目名应与 `pyproject.toml` 中一致：

- `deepseek-balance-monitor-mac`

配置完成后，以后你再推送 `vX.Y.Z` tag，PyPI 发布会自动执行。

另外，还需要在 GitHub 仓库里新增一个 Repository Variable：

- Name: `PYPI_PUBLISH_ENABLED`
- Value: `true`

这样做的目的是：

- 默认不会因为 PyPI 还没配置好而让发布工作流失败
- 当你确认 PyPI 已准备好后，只要打开这个变量即可自动发布

## 5. 如果暂时不想自动发 PyPI

即使还没有配置 PyPI Trusted Publisher，或者没有开启 `PYPI_PUBLISH_ENABLED=true`：

- GitHub Release 自动上传仍然可以正常使用
- `publish-pypi` 会被直接跳过，不会影响 Release 成功

## 6. 产物清单

自动上传到 GitHub Release 的文件包括：

- `DeepSeek-Balance-Monitor-mac.zip`
- `DeepSeek-Balance-Monitor-mac.dmg`
- `deepseek_balance_monitor_mac-*.whl`
- `deepseek_balance_monitor_mac-*.tar.gz`
- `SHA256SUMS.txt`
