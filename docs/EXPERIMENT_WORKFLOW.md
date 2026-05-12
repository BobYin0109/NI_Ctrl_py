# Experiment Workflow

## 1. Software Checks

```powershell
python -m pytest
ni-ctrl plan --config configs/full_48_52_50nm.json
ni-ctrl dry-run --config configs/full_48_52_50nm.json
```

The full production plan should report `81 positions`.

## 2. NI Trigger Check

Use an oscilloscope or suitable meter to verify the TTL trigger line before connecting the camera.

```powershell
ni-ctrl test-pulse --line Dev1/port2/line5 --count 10 --pulse-width-s 0.005
```

If the NI device name is not `Dev1`, update both JSON config files.

## 3. PI Stage Check

Close PI MikroMove before running Python so only one program controls the E-727.

```powershell
ni-ctrl test-pi --config configs/small_test.json --axis z --position-um 50.05
```

Use a small safe displacement first.

## 4. Small Imaging Test

Set the CMOS software to external trigger mode, then run:

```powershell
ni-ctrl scan --config configs/small_test.json --confirm-hardware
```

Confirm:

- Stage reaches each Z position.
- One image is captured per trigger.
- CSV log appears under `logs/`.
- No missed frames.

## 5. Production Z Stack

After the small test is correct:

```powershell
ni-ctrl scan --config configs/full_48_52_50nm.json --confirm-hardware
```

This scans from `48.00 um` to `52.00 um` with `0.05 um` steps.

## 6. Notes on Timing

The current implementation is software-coordinated:

1. Move PI stage.
2. Wait until PI reports on target.
3. Wait the configured settle time.
4. Emit one NI digital pulse.

This is appropriate for step-and-shoot bead imaging. If a later experiment needs pulse timing with strict sub-millisecond determinism, move the pulse generation to a hardware-timed NI counter task and keep Python as the high-level coordinator.
