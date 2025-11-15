# 记忆上下文驱动的规划型机器人 Agent（Python + GPT-4o，无前端）

## 项目概述
- 以“记忆 + 规划”为核心的机器人风格 AI Agent：自然语言 → 分层规划（简化 HTN）→ A* 导航 → 动态重规划 → 自我反思更新记忆 → 报告与评测。
- 纯 Python 标准库实现，LLM 可选（GPT-4o）；不依赖 ROS/数据库，持久化使用 JSON/JSONL。

## 主要特性
- 记忆系统：Episodic（事件流）、Semantic（地点/障碍/高代价区）、Procedural（技能统计/提示）、Working（任务上下文）。
- 规划执行：从任务文本抽取地点顺序与优先级；A* 路径规划结合语义代价；遇障即时重规划并写入记忆。
- 评测对比：批量任务、生成“有记忆 vs 无记忆”的指标表与 SVG 曲线，便于简历展示。

## 快速开始
- 运行环境：`python3`，推荐安装依赖：`pip install -r requirements.txt`
- 克隆后在项目根目录执行示例：
  - 仅生成计划：`python3 -m agent.cli show_plan "在30分钟内巡检A→B→C，优先A，拥堵则绕行" --api_key "你的Key" --base_url "https://api.chatanywhere.tech/v1"`
  - 执行并生成报告：`python3 -m agent.cli run "在30分钟内巡检A→B→C，优先A，拥堵则绕行" --api_key "你的Key" --base_url "https://api.chatanywhere.tech/v1"`
- 输出文件在 `out/`：
  - `plan.json`（规划步骤与约束）
  - `trajectory.json`（位姿轨迹）
  - `logs.json`（执行日志）
  - `report.md`（可读报告）
  - `map_trajectory.svg`（地图+轨迹可视化，含热力与阻塞标记）
  - `anim.svg`（动画仿真：机器人沿轨迹移动）

## LLM 配置（无需环境变量）
- 在命令行传入：`--api_key "你的Key" --base_url "你的BaseURL"`
- 接入逻辑：`agent/core/llm.py:6-15` 通过 `configure(api_key, base_url)` 注入；Planner 在 `agent/core/planner.py:6-15` 调用 LLM 生成 JSON 步骤（无 Key 时回退为规则解析）。

## 目录结构
- `agent/cli.py`：命令入口（`show_plan`/`run`/`eval`）
- `agent/core/planner.py`：任务解析与步骤生成（LLM + 规则）
- `agent/core/navigator.py`：A* 路径规划与语义代价
- `agent/core/executor.py`：执行仿真与遇障重规划
- `agent/core/memory.py`：记忆读写、检索与事后反思更新
- `agent/core/reporter.py`：导出报告与原始数据
- `agent/core/charts.py`：评测指标转 SVG 曲线
- `maps/`：栅格地图与命名地点
- `memory/`：长期记忆（JSON/JSONL）
- `eval/`：批量任务文件

## 使用说明
- 仅规划：`python3 -m agent.cli show_plan "任务文本" --api_key "Key" --base_url "BaseURL"`
- 执行：`python3 -m agent.cli run "任务文本" --api_key "Key" --base_url "BaseURL"`
- 批量评测：
  - 编辑 `eval/tasks.txt`（每行一个任务文本）
  - 运行：`python3 -m agent.cli eval eval/tasks.txt --api_key "Key" --base_url "BaseURL"`
  - 结果：`out/metrics.csv`、`out/metrics.svg`

## 数据文件
- 地图：`maps/grid.json`（0 可走 / 1 障碍）、`maps/locations.json`（命名地点 `{name,x,y,r,tags}`）
- 配置：`config.json`（起点、重试、代价权重等）
- 记忆：
  - `memory/episodic.jsonl`（逐步追加事件）
  - `memory/semantic.json`（高代价区/障碍/别名/时间窗）
  - `memory/procedural.json`（技能统计与提示）

## 记忆即上下文（工作流程）
- 执行时写入 Episodic；任务结束调用反思将关键经验合并至 Semantic/Procedural；下次规划前检索 Top-K 记忆并融合为上下文，影响排序与路径代价。

## 关键代码引用
- 命令入口与子命令：`agent/cli.py:61-78`
- 规划与约束解析：`agent/core/planner.py:6-15`、顺序与优先级解析在 `agent/core/planner.py:17-49`
- A* 路径与语义代价：`agent/core/navigator.py:8-52`
- 执行与重规划：`agent/core/executor.py:12-40`
- 记忆检索与反思更新：`agent/core/memory.py:43-85`
- 评测与图表：`agent/cli.py:107-127`、`agent/core/charts.py`

## 评测与展示
- 运行：`python3 -m agent.cli eval eval/tasks.txt --api_key "Key" --base_url "BaseURL"`
- 指标：时间 `time_sec`、路径长度 `path_len`、阻塞次数 `blocked`
- 曲线：`out/metrics.svg`（内置时间对比柱状图，灰色=基线，无记忆；绿色=记忆）

## 简历描述示例
- 构建“记忆上下文驱动”的规划型机器人 Agent（Python + GPT-4o），以 JSON 持久化实现四类记忆，完成自然语言→分层规划→A* 动态重规划→自反思更新闭环；支持批量评测并输出“有记忆 vs 无记忆”的对比指标与曲线，在数字孪生场景显著提升效率与稳定性。

## 路线图（可选）
- 记忆摘要压缩 → 更强的 LLM 引导（把 Top-K 记忆要点注入 system 提示）
- 更严格的时间窗与优先级调度（贪心近似/TSPTW）
- 评测维度扩展（重规划次数、改道成本、成功率）及更丰富图表
