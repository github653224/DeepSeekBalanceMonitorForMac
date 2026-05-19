# 贡献指南

感谢你关注这个项目。

当前仓库以 mac 版本为主，欢迎围绕以下方向参与：

- bug 修复
- 菜单栏体验优化
- 设置窗口和历史窗口优化
- 打包和发布流程优化
- 测试补充
- 文档补充

## 本地环境

推荐使用 conda 环境，并使用 `uv pip install` 安装依赖：

```bash
source /Users/rock/miniconda3/bin/activate deepseek-balance-monitor-mac
cd /Users/rock/Documents/DeepSeekBalanceMonitorForMac
uv pip install -e '.[build]'
```

## 本地运行

```bash
python main.py
```

## 运行测试

```bash
python -m unittest tests.test_core
python -m py_compile main.py src/deepseek_balance_monitor_mac/mac/main.py
```

## 打包验证

```bash
bash scripts/build_mac.sh
bash scripts/build_dmg.sh
python -m build
```

## 提交建议

- 尽量一次提交只解决一个问题
- 优先保持 mac 主线稳定
- 不要顺手做大范围无关重构
- 改 UI 时尽量附截图
- 改打包流程时尽量写清楚验证步骤

## 安全要求

请不要提交以下内容：

- 真实 API Key
- 本地配置文件
- 本地数据库
- 本地日志
- `build/`、`dist/`、`*.egg-info/`、`__pycache__/`

## Issue / PR 建议

提交 PR 时建议说明：

- 改了什么
- 为什么改
- 怎么验证
- 是否影响打包或兼容性
