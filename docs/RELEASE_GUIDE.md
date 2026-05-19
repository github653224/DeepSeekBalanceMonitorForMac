# 发布指南

## 1. 发布目标

当前建议同时维护三类产物：

- GitHub 源码仓库
- mac 分发包：`.app`、`.zip`、`.dmg`
- PyPI 包：`wheel` + `sdist`

其中：

- GitHub 适合开源协作和源码分发
- `.dmg` 适合普通 mac 用户安装
- PyPI 适合开发者安装和后续自动化分发

## 2. 发布前检查

每次发布前建议先做这几步：

1. 确认 `pyproject.toml` 中版本号已更新
2. 确认 `CHANGELOG.md` 已补充本次变化
3. 确认没有真实 API Key、日志、数据库、缓存被提交
4. 跑一次测试
5. 跑一次源码启动
6. 跑一次 `.app` 和 `.dmg` 打包
7. 跑一次 `python -m build`

## 3. 本地发布命令

进入环境：

```bash
source /Users/rock/miniconda3/bin/activate deepseek-balance-monitor-mac
cd /Users/rock/Documents/DeepSeekBalanceMonitorForMac
```

安装依赖：

```bash
uv pip install -e '.[build]'
```

运行测试：

```bash
python -m unittest tests.test_core
```

构建 `.app`：

```bash
bash scripts/build_mac.sh
```

构建 `.dmg`：

```bash
bash scripts/build_dmg.sh
```

构建 PyPI 包：

```bash
python -m build
```

校验包：

```bash
twine check dist/*.whl dist/*.tar.gz
```

## 4. GitHub 发布建议

推荐仓库里只提交源码、文档和脚本，不提交本地构建产物。

通常不建议提交：

- `build/`
- `dist/`
- `*.egg-info/`
- `__pycache__/`
- 本机日志
- 本机数据库
- 本机配置文件

推荐在 GitHub Release 页面上传这些二进制产物：

- `DeepSeek Balance Monitor.app.zip`
- `DeepSeek-Balance-Monitor-mac.dmg`

如果你希望用户更容易下载，也可以在 Release 里附带 SHA-256。

## 5. PyPI 发布建议

建议先发 TestPyPI，再发正式 PyPI。

上传到 TestPyPI：

```bash
twine upload --repository testpypi dist/*
```

上传到正式 PyPI：

```bash
twine upload dist/*
```

建议习惯：

- 每次发布都同步打 tag
- wheel 和 sdist 一起上传
- 先本地安装验证一次再上传

## 6. 本地安装验证

可以在一个干净环境里验证：

```bash
pip install dist/deepseek_balance_monitor_mac-0.1.0-py3-none-any.whl
deepseek-balance-monitor
```

或：

```bash
python -m pip install dist/deepseek_balance_monitor_mac-0.1.0.tar.gz
```

## 7. 关于 Intel 和 M 系列

当前 PyInstaller 构建出来的 `.app` 通常是和当前机器架构相关的。

也就是说：

- 在 Apple Silicon 机器上打包，默认更偏向 arm64
- 如果要更稳地兼容 Intel 与 M 系列，后续可以考虑：
  - 分别构建 `arm64` 和 `x86_64`
  - 或研究 Universal 2 打包路线

第一阶段建议先把当前机器可用的版本做好，然后再补双架构发布策略。

## 8. 版本发布建议节奏

建议这样做：

1. `0.1.x`：把 mac 主线稳定住
2. `0.2.x`：补 CI、截图、安装说明、更多测试
3. `0.3.x`：优化打包和签名、公证流程
4. `1.0.0`：功能、文档、发布链路都成熟后再定
