# 久坐提醒器 (Sight Habit Keeper)

> 一款轻量级的桌面久坐提醒工具，帮助你养成定时起身活动的好习惯。

![Python](https://img.shields.io/badge/Python-3.6+-blue?logo=python)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-green)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 目录

- [功能特性](#功能特性)
- [效果预览](#效果预览)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [使用说明](#使用说明)
- [打包发布](#打包发布)
- [项目结构](#项目结构)
- [技术实现](#技术实现)
- [常见问题](#常见问题)
- [更新日志](#更新日志)

---

## 功能特性

- ✅ **自定义倒计时** — 自由设置提醒间隔（默认30分钟），以分钟为单位
- ✅ **实时时间显示** — 窗口顶部显示当前系统时间，每秒刷新
- ✅ **倒计时可视化** — 动态显示剩余 `MM:SS` 格式倒计时
- ✅ **模态弹窗提醒** — 时间到后弹出置顶提醒窗口，强制引起注意
- ✅ **自动循环计时** — 点击"确定"后自动开始下一轮计时，无需手动操作
- ✅ **开始 / 停止控制** — 可随时手动停止或重新开始计时
- ✅ **纯 Python 实现** — 无需额外依赖，标准库即可运行
- ✅ **无后台进程** — 纯 GUI 应用，关闭即退出

---

## 效果预览

| 界面区域 | 说明 |
|---------|------|
| ![][clock] 时间显示区 | 显示当前系统时间，格式 `YYYY-MM-DD HH:MM:SS` |
| ![][status] 状态显示区 | 显示"准备启动"、"工作中（剩余29:30）"、"时间到！请起身活动"等状态 |
| ![][input] 倒计时设置 | 输入框，可自定义倒计时分钟数 |
| ![][btn] 开始 / 停止按钮 | 控制计时器的启动与停止，互斥状态切换 |
| ![][alert] 弹窗提醒 | 时间到后置顶弹出："您已连续工作XX分钟，请离开座位！" |

---

## 环境要求

- **Python** 3.6 或更高版本（自带 tkinter 标准库）
- **操作系统**：Windows（其他平台理论上可运行，需自行适配图标格式）
- **额外依赖**：无（仅使用 Python 标准库）

---

## 快速开始

### 1️⃣ 直接运行源码

```bash
# 克隆或下载项目后，进入项目目录
cd 久坐提醒

# 直接运行（无需安装任何第三方库）
python Sight_Habit_Keeper.py
```

### 2️⃣ 打包为可执行文件（推荐）

使用 [PyInstaller](https://pyinstaller.org/) 打包为 `.exe`：

```bash
# 安装 PyInstaller
pip install pyinstaller

# 方式一：使用 spec 文件打包（推荐）
pyinstaller Sight_Habit_Keeper.spec

# 方式二：手动命令打包
pyinstaller --onefile --windowed --icon=walking_icon.ico --name=Sight_Habit_Keeper Sight_Habit_Keeper.py
```

打包后在 `dist` 目录下即可获得 `Sight_Habit_Keeper.exe`，双击运行。

---

## 使用说明

1. **启动程序** — 双击运行或 `python Sight_Habit_Keeper.py`
2. **设置间隔** — 在输入框中填写希望提醒的间隔分钟数（默认 30）
3. **开始计时** — 点击「开始计时」按钮，状态显示倒计时
4. **收到提醒** — 时间到后自动弹出置顶弹窗，提示起身活动
5. **继续工作** — 点击弹窗「确定」，计时器自动重新开始新一轮
6. **停止计时** — 点击「停止计时」可随时暂停；再次点击「开始计时」继续

> **提示**：推荐设置 25~45 分钟，符合番茄工作法或眼科建议的用眼时长。

---

## 打包发布

### 使用 `.spec` 文件

项目已内置 `Sight_Habit_Keeper.spec`，可直接使用 PyInstaller 打包：

```bash
pyinstaller Sight_Habit_Keeper.spec
```

`s`pec 文件关键配置说明：

| 配置项 | 值 | 说明 |
|-------|-----|------|
| `console` | `False` | 不显示命令行窗口 |
| `windowed` | （通过 `console=False` 实现） | GUI 模式运行 |
| `icon` | `walking_icon.ico` | 程序图标（行走小人） |
| `onefile` | 单文件打包 | 所有资源整合为一个 `.exe` |

### 输出文件

```
dist/
└── Sight_Habit_Keeper.exe   ← 可直接分发的可执行文件
```

---

## 项目结构

```
久坐提醒/
├── Sight_Habit_Keeper.py      # 主程序入口
├── Sight_Habit_Keeper.spec    # PyInstaller 打包配置文件
├── README.md                  # 本文档
├── .gitignore                 # Git 忽略规则
├── assets/
│   └── walking_icon.ico       # 程序图标（行走人物）
└── archive/
    └── Sight_Habit_Keeper_bkp.py  # 旧版备份（硬编码 30 分钟）
```

### 版本差异

| 文件 | 说明 |
|------|------|
| `Sight_Habit_Keeper.py` | **当前主版本**，支持自定义倒计时时长、输入校验 |
| `archive/Sight_Habit_Keeper_bkp.py` | 旧版备份，倒计时时长硬编码为 30 分钟，无输入框 |

---

## 技术实现

### 核心技术方案

- **GUI 框架**：Python 内置 `tkinter`，零依赖
- **计时方案**：`root.after()` 递归调用替代多线程，避免 tkinter 线程安全问题
- **时间计算**：`datetime.now()` 实时计算已过时间与剩余时间，保证精度

### 核心代码逻辑

```
[启动] → 开始计时 → 每秒更新剩余时间（after 递归）
                         ↓
                    剩余 ≤ 0 ?
                    ↙         ↘
                  是           否 → 继续每秒更新
                   ↓
               弹出置顶提醒弹窗
                   ↓
               用户点击"确定"
                   ↓
             自动重新开始计时 → 循环
```

### 关键设计说明

1. **无线程安全风险**：全程使用 `after()` 在主线事件循环中调度，无需 `threading` 或 `queue`
2. **防误操作**：计时中禁用"开始"按钮并禁用分钟输入框，避免误修改
3. **置顶弹窗**：提醒弹窗前设置 `topmost=1`，确保弹窗不会被其他窗口遮挡
4. **自动循环**：用户点击确定后自动调用 `start_timer()`，实现无间断计时

---

## 常见问题

### Q：提示 "tkinter 模块未找到"？

确保 Python 安装时勾选了 **tcl/tk** 组件。Linux 用户可能需要：
```bash
# Ubuntu / Debian
sudo apt install python3-tk

# CentOS / RHEL
sudo yum install python3-tkinter
```

### Q：打包后的 exe 提示缺少图标？

确保 `walking_icon.ico` 与 `Sight_Habit_Keeper.py` 在同一目录下，或在 `.spec` 中正确配置 `icon` 路径。

### Q：如何修改提醒文字？

编辑 `Sight_Habit_Keeper.py` 第 141 行附近的 `messagebox.showinfo(...)` 中的文本内容即可。

### Q：关闭弹窗后计时器自动重启，不需要这个功能怎么办？

可以删除 `Sight_Habit_Keeper.py` 第 145 行的 `self.start_timer()`，改为 `return`。

---

## 更新日志

### v1.1（当前版本）

- ✨ 新增自定义倒计时时长输入（原为固定 30 分钟）
- ✨ 新增输入校验（仅接受正数，错误时弹出警告）
- ✨ 新增 `walking_icon.ico` 程序图标
- 🔧 优化 UI 布局：按功能分区（时间区 / 设置区 / 按钮区）
- 🔧 打包配置（`.spec`）支持图标与无窗口模式

### v1.0（备份版本）

- 🎉 初始版本，固定 30 分钟倒计时
- 🎉 基本 GUI 界面，开始 / 停止控制
- 🎉 置顶弹窗提醒 + 自动循环计时

---

## 许可

本项目基于 MIT 许可协议开源，详情请参阅 `LICENSE` 文件（如适用）。

---

*保持好习惯，从久坐提醒开始。站起来，走两步，眼睛和腰椎会感谢你。*
