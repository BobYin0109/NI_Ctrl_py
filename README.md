# NI Ctrl Py

Python project for step-and-shoot super-resolution bead imaging with:

- PI E-727.3CD nano XYZ piezo controller over USB/RS-232/GCS
- NI PCIe-6353 + SCB-68A digital trigger output
- CMOS camera in external-trigger mode

The tested production scan plan is:

- Z range: `49.000 um` to `51.000 um`
- Step: `0.010 um` / `10 nm`
- Positions: `201`
- Sequence: move Z -> wait on target -> settle -> TTL trigger -> log
- End behavior: return Z to `50.00 um`

## Safety Model

This project intentionally separates motion control and camera triggering:

- PI E-727.3CD controls the piezo stage through PI commands.
- NI PCIe-6353 outputs TTL trigger pulses to the CMOS `EXT. TRIG` input.
- Optional CMOS timing outputs can be wired back to NI digital inputs for diagnostics.
- Camera image data remains handled by the camera data cable and acquisition software unless a camera SDK is added later.

Do not connect NI analog output to this E-727.3CD setup.

## Install

On the acquisition computer:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pip install -e ".[hardware]"
```

Required vendor software:

- PI drivers / PI software suite, with E-727 visible through USB or RS-232
- NI-DAQmx driver, with PCIe-6353 visible in NI MAX
- CMOS acquisition software set to external trigger mode

## Dry Run

Check the full 49-51 um / 10 nm plan without touching hardware:

```powershell
ni-ctrl plan --config configs/z_stack_201_49_51_10nm.json
ni-ctrl dry-run --config configs/z_stack_201_49_51_10nm.json
```

## Hardware Bring-Up

Run these in order after wiring is checked.

1. Confirm the NI device name in NI MAX, for example `Dev1`.
2. Verify the trigger line with an oscilloscope before connecting the camera:

```powershell
ni-ctrl test-pulse --line Dev1/port2/line5 --count 10 --pulse-width-s 0.005
```

3. Confirm small PI motion:

```powershell
ni-ctrl test-pi --config configs/small_test.json --axis z --position-um 50.05
```

4. Dry-run the small scan:

```powershell
ni-ctrl dry-run --config configs/small_test.json
```

5. Run the small hardware scan:

```powershell
ni-ctrl scan --config configs/small_test.json --confirm-hardware
```

6. After the small scan is correct, run the tested 201-image production scan:

```powershell
ni-ctrl scan --config configs/z_stack_201_49_51_10nm.json --confirm-hardware
```

## Expected Wiring Candidates

The project defaults match the local experiment notes:

- CMOS `EXT. TRIG` center -> SCB-68A Terminal 40 -> `Dev1/port2/line5`
- CMOS `EXT. TRIG` shield -> SCB-68A Terminal 7 / D GND
- CMOS `TIMING OUT` center -> SCB-68A Terminal 41 -> `Dev1/port1/line4`
- CMOS `TIMING OUT` shield -> SCB-68A Terminal 9 / D GND

Treat these as candidates until verified against NI MAX, the SCB-68A connector label, and a scope measurement.

## Tested HCImageLive Setup

Use `configs/hcimagelive_mono_external_trigger.json` as the camera-side settings record.

Key tested settings:

- Capture preset: `Mono: 1 Channel`
- Capture mode: `External Edge Trigger`
- Trigger edge: `Pos`
- Sequence: `Time Lapse`
- AutoSave: `TIFF`, `to Disk`
- Control: `End Frame`
- End frame for the 49-51 um / 10 nm stack: `201`
- Nikon Eclipse Ti2 auto focus lock: disabled

With `Mono: 1 Channel`, one NI trigger saves one TIFF image. During local testing,
`RGB Color: 2-Band` required two triggers per saved TIFF.

See `docs/RUNBOOK_2026_05_13.md` for the full tested workflow.

## Development

The unit tests do not require PI or NI hardware:

```powershell
python -m pytest
python -m ruff check .
```

Project layout:

```text
src/ni_ctrl_py/       Python package
configs/              Experiment configuration files
docs/                 Wiring and operating workflow
tests/                Hardware-free tests
.github/workflows/    GitHub Actions CI
```
