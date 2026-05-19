# 开发指南

## 1. 项目目标

这个仓库是 DeepSeek Balance Monitor 的独立 mac 产品线。

当前阶段重点：

- 做好 mac 菜单栏主线
- 保持原生设置窗口与历史窗口体验
- 支持源码运行、`.app` 打包、`.dmg` 打包
- 为后续 GitHub 开源与 PyPI 发布打基础

这个仓库目前不是 Windows / Linux 共用仓库，而是 mac 优先的独立工程。

## 2. 技术形态

当前应用形态是：

- macOS 菜单栏应用
- 不是传统主窗口桌面应用
- 启动后常驻菜单栏
- 设置、历史、提醒通过原生窗口和系统通知完成

核心依赖大致包括：

- `rumps`：菜单栏应用
- `tkinter`：设置与历史窗口
- `requests`：调用 DeepSeek API
- `sqlite3`：本地历史数据
- `cryptography`：本地安全存储
- `PyInstaller`：打包 `.app`

## 3. 目录结构

```text
DeepSeekBalanceMonitorForMac/
  main.py
  pyproject.toml
  README.md
  AGENTS.md
  LICENSE
  CONTRIBUTING.md
  CHANGELOG.md
  SECURITY.md
  docs/
    DEVELOPMENT_GUIDE.md
    RELEASE_GUIDE.md
  scripts/
    build_mac.sh
    build_dmg.sh
    DeepSeekBalanceMonitor.spec
  src/
    deepseek_balance_monitor_mac/
      __init__.py
      __main__.py
      api_client.py
      app_state.py
      config.py
      credential_store.py
      history_dialog.py
      icon_renderer.py
      secure_settings.py
      storage.py
      core/
      infra/
      mac/
      assets/
  tests/
    test_core.py
```

## 4. 环境准备

推荐统一使用你的 conda 环境，再配合 `uv pip install` 安装依赖。

```bash
source /Users/rock/miniconda3/bin/activate deepseek-balance-monitor-mac
cd /Users/rock/Documents/DeepSeekBalanceMonitorForMac
uv pip install -e '.[build]'
```

如果某些场景下需要回退，也可以用：

```bash
python3 -m pip install -e . --no-deps
python3 -m pip install build twine
```

## 5. 运行方式

源码运行：

```bash
python main.py
```

或：

```bash
python -m deepseek_balance_monitor_mac
```

如果本机还没有配置 API Key，应用会自动引导到设置窗口。

## 6. 常用开发命令

安装依赖：

```bash
uv pip install -e '.[build]'
```

运行应用：

```bash
python main.py
```

运行单元测试：

```bash
python -m unittest tests.test_core
```

检查关键入口：

```bash
python -m py_compile \
  main.py \
  src/deepseek_balance_monitor_mac/mac/main.py \
  src/deepseek_balance_monitor_mac/mac/settings.py
```

## 7. 打包 `.app`

```bash
bash scripts/build_mac.sh
```

产物：

- `dist/DeepSeek Balance Monitor.app`
- `dist/DeepSeek-Balance-Monitor-mac.zip`

说明：

- 脚本会重新生成图标
- 使用 PyInstaller 构建 `.app`
- 进行 ad-hoc codesign
- 自动产出一个便于分发的 zip

## 8. 打包 `.dmg`

先确保 `.app` 已经生成：

```bash
bash scripts/build_mac.sh
```

再执行：

```bash
bash scripts/build_dmg.sh
```

产物：

- `dist/DeepSeek-Balance-Monitor-mac.dmg`

## 9. 打包 Python 包

```bash
python -m build
```

产物：

- `dist/*.whl`
- `dist/*.tar.gz`

这些包主要服务于：

- PyPI 发布
- 内部测试安装
- 以后做命令行入口或轻量安装分发

## 10. 测试建议

当前已经有基础测试：

```bash
python -m unittest tests.test_core
```

手工验证建议至少覆盖：

- 首次启动无 API Key
- 保存设置后再次打开仍能回填
- 人民币 / 美元切换
- 余额显示与服务状态显示
- 今日消耗与日均消耗显示
- 低余额提醒
- 今日消耗阈值提醒
- 历史窗口打开与 CSV 导出
- `.app` 与 `.dmg` 启动可用

## 11. 配置与数据

这个应用运行时会把用户配置和数据放在本机目录中，不会写回仓库源码。

因此：

- 打包出来的 `.app` 默认不应该携带你的 API Key
- 其他用户首次打开时，应看到设置引导
- 只有用户自己在本机输入 API Key 后，应用才能查询余额

这也是开源和分发时比较安全、比较顺滑的方式。

## 12. 为什么只需要 API Key

因为应用直接调用 DeepSeek 提供的余额接口：

- `GET https://api.deepseek.com/user/balance`

并通过：

- `Authorization: Bearer <API_KEY>`

来完成身份校验。

所以这个项目不是网页登录型应用，而是 API Key 直连型工具。

## 13. 建议开发顺序

建议后续按这个顺序推进：

1. 稳定 mac 功能和 UI
2. 完善 GitHub 开源材料
3. 完善发布流程
4. 上 TestPyPI
5. 上正式 PyPI
6. 加 GitHub Actions 自动化
7. 再考虑抽取跨平台共享核心
8. Windows / Linux / 移动端分阶段独立推进

## 14. 新开会话是否更省 token

是的。

既然现在已经把 mac 主线独立到：

- `/Users/rock/Documents/DeepSeekBalanceMonitorForMac`

后续如果继续围绕这个新项目开发，建议重新开启一个新会话，并直接让新会话从这个目录开始工作。

这样会更干净，历史上下文更聚焦，也更省 token。
