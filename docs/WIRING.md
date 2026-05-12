# Wiring Notes

This document records the intended wiring for the current PI E-727.3CD + NI PCIe-6353 + SCB-68A + CMOS setup.

## Role Separation

- PI E-727.3CD: stage motion only, through USB or RS-232.
- NI PCIe-6353 + SCB-68A: digital TTL trigger output and optional timing input.
- CMOS camera: external-triggered image acquisition through its own camera cable/software.

The E-727.3CD variant in this experiment should not be driven through NI analog output.

## Candidate Trigger Wiring

Verify the SCB-68A label and NI MAX device name before connecting the camera.

| Function | Camera side | SCB-68A side | Python line |
| --- | --- | --- | --- |
| Trigger signal | `EXT. TRIG` center conductor | Terminal 40 | `Dev1/port2/line5` |
| Trigger ground | `EXT. TRIG` shield | Terminal 7 / D GND | n/a |
| Timing signal | `TIMING OUT` center conductor | Terminal 10 | `Dev1/port1/line1` |
| Timing ground | `TIMING OUT` shield | Terminal 9 / D GND | n/a |

If NI MAX reports a different device name, replace `Dev1` in the JSON config.

## Before Connecting CMOS

1. Leave the CMOS trigger cable disconnected.
2. Connect oscilloscope probe positive to SCB-68A Terminal 40.
3. Connect oscilloscope ground to SCB-68A Terminal 7.
4. Run:

```powershell
ni-ctrl test-pulse --line Dev1/port2/line5 --count 10 --pulse-width-s 0.005
```

Expected result: a clean TTL pulse relative to digital ground.

Only connect the CMOS `EXT. TRIG` input after this measurement is correct.

## CMOS Settings

Use the camera software to set:

- External trigger mode
- One frame per trigger
- Rising edge trigger, unless the camera manual requires falling edge
- Exposure and save path prepared before running Python

The rear-panel connector type does not change the software plan. For each coaxial trigger/timing line, the center conductor is the signal and the shield is ground.
