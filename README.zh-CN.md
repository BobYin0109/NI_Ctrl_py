# NI Ctrl Py

[English](README.md)

用于逐点拍摄超分辨微球图像的 Python 项目，硬件包括：

- 通过 USB/RS-232/GCS 控制的 PI E-727.3CD 纳米 XYZ 压电位移控制器
- NI PCIe-6353 + SCB-68A 数字触发输出
- 工作在外部触发模式下的 CMOS 相机

仓库记录了 201 帧硬件联调流程。当前版本以扫描启动时从 PI 位移台读取的 Z 位置为中心：

- Z 范围：相对起始中心 ±1.000 µm
- 步长：`0.010 um` / `10 nm`
- 位置数：`201`
- 流程：移动 Z -> 等待到位 -> 稳定等待 -> TTL 触发 -> 记录日志
- 结束行为：Z 返回扫描启动时读取的中心

配置文件名沿用最初的 49–51 µm 示例。启用
`positions.use_current_z_as_center` 后，配置中的中心和端点用于计算相对偏移，再平移到实时 Z。
平移后的扫描必须落在配置的绝对 Z 安全范围内。此配置的 `plan` 和 `dry-run` 按 50 µm 中心预览，不读取实际位移台。

## 安全模型

本项目有意将位移控制和相机触发分开：

- PI E-727.3CD 通过 PI 指令控制压电位移台。
- NI PCIe-6353 向 CMOS 的 `EXT. TRIG` 输入输出 TTL 触发脉冲。
- 可选的 CMOS timing 输出可以接回 NI 数字输入，用于诊断。
- 除非后续接入相机 SDK，否则相机图像数据仍由相机数据线和采集软件处理。

不要将 NI 模拟输出连接到这套 E-727.3CD 系统。

## 安装

在图像采集电脑上运行：

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pip install -e ".[hardware]"
```

需要安装的厂商软件：

- PI 驱动 / PI 软件套件，并确保 E-727 可通过 USB 或 RS-232 识别
- NI-DAQmx 驱动，并确保 PCIe-6353 可在 NI MAX 中识别
- 设置为外部触发模式的 CMOS 采集软件

## Dry Run

在不连接硬件的情况下检查 ±1 µm、10 nm 步进的扫描方案：

```powershell
ni-ctrl plan --config configs/z_stack_201_49_51_10nm.json
ni-ctrl dry-run --config configs/z_stack_201_49_51_10nm.json
```

## 硬件联调

确认接线后，按以下顺序运行。

1. 在 NI MAX 中确认 NI 设备名，例如 `Dev1`。
2. 连接相机前，先用示波器验证触发线：

```powershell
ni-ctrl test-pulse --line Dev1/port2/line5 --count 10 --pulse-width-s 0.005
```

3. 确认 PI 小范围运动：

```powershell
ni-ctrl test-pi --config configs/small_test.json --axis z --position-um 50.05
```

4. 对小范围扫描进行 dry-run：

```powershell
ni-ctrl dry-run --config configs/small_test.json
```

5. 运行小范围硬件扫描：

```powershell
ni-ctrl scan --config configs/small_test.json --confirm-hardware
```

6. 小范围扫描确认无误后，运行已经测试过的 201 张正式扫描：

```powershell
ni-ctrl scan --config configs/z_stack_201_49_51_10nm.json --confirm-hardware
```

## 预期接线候选方案

项目默认值与本地实验记录一致：

- CMOS `EXT. TRIG` 中心导体 -> SCB-68A Terminal 40 -> `Dev1/port2/line5`
- CMOS `EXT. TRIG` 屏蔽层 -> SCB-68A Terminal 7 / D GND
- CMOS `TIMING OUT` 中心导体 -> SCB-68A Terminal 41 -> `Dev1/port1/line4`
- CMOS `TIMING OUT` 屏蔽层 -> SCB-68A Terminal 9 / D GND

在使用前，应通过 NI MAX、SCB-68A 连接器标签和示波器测量确认这些映射。

## 已测试的 HCImageLive 设置

使用 `configs/hcimagelive_mono_external_trigger.json` 记录相机侧设置。

关键已测试设置：

- Capture preset：`Mono: 1 Channel`
- Capture mode：`External Edge Trigger`
- Trigger edge：`Pos`
- Sequence：`Time Lapse`
- AutoSave：`TIFF`，`to Disk`
- Control：`End Frame`
- ±1 µm、10 nm 堆栈的 End frame：`201`
- Nikon Eclipse Ti2 自动对焦锁定：关闭

在 `Mono: 1 Channel` 下，一个 NI 触发会保存一张 TIFF 图像。本地测试中，
`RGB Color: 2-Band` 需要两个触发才会保存一张 TIFF。

201 帧流程见[采集操作记录](docs/RUNBOOK_2026_05_13.md)。双通道 SMLM 项目分析的 1 nm 微球扫描使用了另一套采集流程。

## 开发

单元测试不需要 PI 或 NI 硬件：

```powershell
python -m pytest
python -m ruff check .
```

项目结构：

```text
src/ni_ctrl_py/       Python 包
configs/              实验配置文件
docs/                 接线与操作流程
tests/                无硬件测试
.github/workflows/    GitHub Actions CI
```
