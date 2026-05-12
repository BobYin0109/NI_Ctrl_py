# NI Ctrl Py

Python project for step-and-shoot super-resolution bead imaging with:

- PI E-727.3CD nano XYZ piezo controller over USB/RS-232/GCS
- NI PCIe-6353 + SCB-68A digital trigger output
- CMOS camera in external-trigger mode

The default production scan plan is:

- Z range: `48.00 um` to `52.00 um`
- Step: `0.05 um` / `50 nm`
- Positions: `81`
- Sequence: move Z -> wait on target -> settle -> TTL trigger -> log

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

Check the full 48-52 um / 50 nm plan without touching hardware:

```powershell
ni-ctrl plan --config configs/full_48_52_50nm.json
ni-ctrl dry-run --config configs/full_48_52_50nm.json
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

6. After the small scan is correct, run the production scan:

```powershell
ni-ctrl scan --config configs/full_48_52_50nm.json --confirm-hardware
```

## Expected Wiring Candidates

The project defaults match the local experiment notes:

- CMOS `EXT. TRIG` center -> SCB-68A Terminal 40 -> `Dev1/port2/line5`
- CMOS `EXT. TRIG` shield -> SCB-68A Terminal 7 / D GND
- CMOS `TIMING OUT` center -> SCB-68A Terminal 10 -> `Dev1/port1/line1`
- CMOS `TIMING OUT` shield -> SCB-68A Terminal 9 / D GND

Treat these as candidates until verified against NI MAX, the SCB-68A connector label, and a scope measurement.

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
