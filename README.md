# DeepSeek Balance Monitor for Mac

一个面向 macOS 的 DeepSeek 余额监控菜单栏应用。

它会常驻菜单栏，帮助你快速查看余额、今日消耗、日均消耗和服务状态，并在余额不足或消耗异常时提醒你。

## 项目定位

- mac 原生菜单栏应用
- 原生设置窗口
- 原生历史记录窗口
- 支持源码运行
- 支持打包 `.app`
- 支持打包 `.dmg`

当前仓库聚焦 mac 产品线，后续优先围绕 mac 版本持续演进。

## 主要功能

- 查询 DeepSeek API 余额
- 显示人民币 / 美元余额
- 显示今日消耗
- 显示日均消耗
- 显示服务状态
- 低余额提醒
- 今日消耗阈值提醒
- 本地 SQLite 历史记录
- CSV 导出
- 本地安全存储 API Key

## 快速开始

建议先准备好 Python 3.11+ 环境，再安装项目依赖。

```bash
cd /path/to/DeepSeekBalanceMonitorForMac
uv pip install -e '.[build]'
python main.py
```

也可以这样启动：

```bash
python -m deepseek_balance_monitor_mac
```

## 常用开发命令

运行应用：

```bash
python main.py
```

运行测试：

```bash
python -m unittest tests.test_core
```

检查关键入口是否可编译：

```bash
python -m py_compile \
  main.py \
  src/deepseek_balance_monitor_mac/mac/main.py \
  src/deepseek_balance_monitor_mac/mac/settings.py
```

## 打包命令

打包 `.app`：

```bash
bash scripts/build_mac.sh
```

打包 `.dmg`：

```bash
bash scripts/build_dmg.sh
```

## 项目结构

```text
DeepSeekBalanceMonitorForMac/
  main.py
  pyproject.toml
  README.md
  docs/
  scripts/
  src/
    deepseek_balance_monitor_mac/
      core/
      infra/
      mac/
      assets/
  tests/
```

更多说明见：

- [开发指南](docs/DEVELOPMENT_GUIDE.md)
- [发布指南](docs/RELEASE_GUIDE.md)
- [贡献指南](CONTRIBUTING.md)
- [安全说明](SECURITY.md)

## 开源前建议

- 确认代码和文档里没有真实 API Key
- 不提交 `build/`、`dist/`、`*.egg-info/`、`__pycache__/`
- 检查截图和示例数据中是否包含隐私信息
- 推送前先完成一次基础测试和打包验证

## 许可证

本项目使用 MIT License。
