# Experiment Workflow

## 1. Software Checks

```powershell
python -m pytest
ni-ctrl plan --config configs/z_stack_201_49_51_10nm.json
ni-ctrl dry-run --config configs/z_stack_201_49_51_10nm.json
```

The tested 49-51 um / 10 nm production plan should report `201 positions`.

## 2. NI Trigger Check

Use an oscilloscope or suitable meter to verify the TTL trigger line before connecting the camera.

```powershell
ni-ctrl test-pulse --line Dev1/port2/line5 --count 10 --pulse-width-s 0.005
```

If the NI device name is not `Dev1`, update the JSON config files.

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
- The scan returns Z to `z_home_um` after completion.

## 5. Tested 201-Image Z Stack

After the small test is correct, configure HCImageLive using
`configs/hcimagelive_mono_external_trigger.json`, set `End Frame = 201`, choose a
new empty AutoSave folder, disable Nikon Eclipse Ti2 auto focus lock, and click
`Start`.

```powershell
ni-ctrl scan --config configs/z_stack_201_49_51_10nm.json --confirm-hardware
```

This scans from `49.000 um` to `51.000 um` with `0.010 um` steps, for `201`
images. The image-to-Z mapping is:

- `Image1_1.tif` -> `49.000 um`
- `Image1_101.tif` -> `50.000 um`
- `Image1_201.tif` -> `51.000 um`

The scan returns Z to `50.00 um` at the end.

## 6. Notes on Timing

The current implementation is software-coordinated:

1. Move PI stage.
2. Wait until PI reports on target.
3. Wait the configured settle time.
4. Emit the configured number of NI digital pulses.
5. Return Z to `z_home_um` in a `finally` block.

This is appropriate for step-and-shoot bead imaging. If a later experiment needs pulse timing with strict sub-millisecond determinism, move the pulse generation to a hardware-timed NI counter task and keep Python as the high-level coordinator.

`timing.triggers_per_position` defaults to `1`. Keep it at `1` for HCImageLive
`Mono: 1 Channel`. During local testing, `RGB Color: 2-Band` required `2`
triggers per saved TIFF.
