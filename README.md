# Gemini UAV Fire Mission Planner

该项目演示一个“两阶段”无人机集群消防指挥流程：

1. **Step 1（Vision）**：把航拍火场图像交给 Gemini 视觉模型，输出火点（fire points）与区域（zone）划分的 **JSON**。
2. **Step 2（Plan）**：把 Step 1 的区域 JSON 作为情报输入，再由 Gemini 生成“无人机指挥代码”（Python 代码文本），用于调用项目内置的技能函数（如搜索、奔赴火点）。

> 代码入口：`run_step1_vision.py`、`run_step2_plan.py`

---

## 功能概览

- 批量读取 `temp/` 目录下的图片（`.jpg/.jpeg/.png`）。
- 通过 Gemini 生成每张图的分区数据，写入 `out/zones_data.json`。
- 可选：把分区多边形与火点叠加可视化，输出到 `temp/output/*_visualized.png`。
- 基于分区数据生成任务指令代码，写入 `out/missions_plan.json`。

---

## 环境依赖

- Python 3.9+（建议 3.10+）
- 主要依赖：
  - `google-genai`（Gemini SDK）
  - `numpy`、`matplotlib`、`Pillow`（仅用于可视化）

安装示例：

```bash
pip install google-genai numpy matplotlib pillow
```

---

## 配置（API Key + 代理）

### 1) 填写 API Key

将 Gemini API Key 写入：`tools/Key.txt`

项目会在初始化 client 时读取该文件（见 `tools/utils.py`）。

### 2) 代理设置（默认开启）

`tools/utils.py` 会默认设置：

- `HTTP_PROXY=http://127.0.0.1:7897`
- `HTTPS_PROXY=http://127.0.0.1:7897`

如果你不需要代理：

- 直接在 `tools/utils.py` 注释/删除相关环境变量设置；或
- 将端口改为你本机代理实际端口。

---

## 快速开始

### Step 0：准备图片

将待分析的航拍图片放入：`temp/`

支持格式：`.jpg` `.jpeg` `.png`

### Step 1：视觉分析（生成 zones JSON）

```bash
python run_step1_vision.py
```

输出：

- `out/zones_data.json`：按文件名存储每张图的 zone 列表
- 可选可视化：`temp/output/*_visualized.png`

### Step 2：任务规划（生成指令代码）

```bash
python run_step2_plan.py
```

输出：

- `out/missions_plan.json`：按文件名存储对应的“Python 指令代码文本”

---

## 输入/输出数据格式

### Step 1 输出（zones）

每张图像对应一个 zone 列表（见 `data/prompts.py` 的约束），典型结构：

- `id`: `zone_0`/`zone_1`...
- `risk_level`: `High` / `Low` / `Monitor`
- `coordinates`: 区域多边形顶点（0~1 归一化坐标）
- `fire_points`: 该区域内火点坐标列表（Monitor 必须为空列表）
- `reason` / `boundary_description`: 解释字段

> Step 1 代码会尝试清理 ```json 包裹后再解析（`run_step1_vision.py`）。

### Step 2 输出（missions_plan）

`out/missions_plan.json` 里每个 value 是一段 **Python 代码字符串**，用于调用技能函数（定义在 `data/function.py`），例如：

- `SearchArea([...], [[x,y], ...])`
- `FlyToFire([...], [x,y])`

无人机资源与状态定义来自：`data/UAV.py`。

---

## 目录结构

```
.
├─ run_step1_vision.py          # Step 1：视觉分析（图片→zones JSON）
├─ run_step2_plan.py            # Step 2：任务规划（zones→指令代码）
├─ data/
│  ├─ prompts.py                # Step 1 的视觉提示词（输出 JSON 约束）
│  ├─ function.py               # “技能函数库”（SearchArea/FlyToFire 等）
│  └─ UAV.py                    # 无人机资产与状态定义
├─ tools/
│  ├─ utils.py                  # 初始化 Gemini Client（读 Key + 代理）
│  ├─ generate.py               # 构建 Step 2 的动态 Prompt（函数/资源/示例）
│  ├─ visualization.py          # zone + fire_points 可视化
│  ├─ rename.py                 # 批量重命名 image/ 下图片（可选工具）
│  └─ Key.txt                   # API Key（需要自己填写）
├─ temp/                        # 输入图片目录（Step 1 扫描该目录）
└─ out/                         # 输出 JSON（zones_data.json / missions_plan.json）
```