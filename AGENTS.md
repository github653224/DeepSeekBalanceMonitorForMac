# Repository Guidelines

## 项目结构

这个仓库是 DeepSeek Balance Monitor 的独立 mac 产品线，后续以 mac 菜单栏主线为核心继续开发。

- 运行时代码：`src/deepseek_balance_monitor_mac/`
- mac 主入口：`src/deepseek_balance_monitor_mac/mac/main.py`
- 设置窗口：`src/deepseek_balance_monitor_mac/mac/settings.py`
- 共享核心：`src/deepseek_balance_monitor_mac/core/`
- 基础设施：`src/deepseek_balance_monitor_mac/infra/`
- 历史与存储：`history_dialog.py`、`storage.py`
- 打包脚本：`scripts/`
- 测试：`tests/`
- 项目文档：`docs/`

## 常用命令

```bash
source /Users/rock/miniconda3/bin/activate deepseek-balance-monitor-mac
cd /Users/rock/Documents/DeepSeekBalanceMonitorForMac
uv pip install -e '.[build]'
python main.py
python -m unittest tests.test_core
bash scripts/build_mac.sh
bash scripts/build_dmg.sh
python -m build
```

## 开发约定

- 优先做小步、兼容性好的修改，不轻易扩散重构范围。
- 保持 mac 优先，Windows / Linux 不作为当前仓库的主设计中心。
- 不要把真实 API Key、日志、数据库、配置文件或打包产物提交进仓库。
- 打包后的 `.app` 不应携带开发机上的本地 API Key。
- 新增说明文档优先写中文，方便后续直接开源维护。
