# Dynamic Boost lost at boot after confining nvidia-powerd

## Overview

On 2026-11-03, after the reboots that followed the confinement of `nvidia-powerd`, the GPU power
limit reported by `nvidia-smi -q -d POWER` stayed at the default 100 W instead of rising to 140 W,
and the daemon logged `QBoost is not created/already destroyed` every second. The confinement had
been validated the day before by restarting the daemon, not by booting the machine.

Affected configuration:

| Component | Version |
| --- | --- |
| `nvidia-powerd` | 2.0, driver 595, confined in `modules/hardware/nvidia.nix` with `ProtectKernelModules` |
| Kernel | zen 7.2.9 |

Cause: Dynamic Boost reads and writes the CPU model-specific registers through `/dev/cpu/*/msr`,
which exists only once the `msr` kernel module is loaded. Unconfined, the daemon loaded that
module itself at start. `ProtectKernelModules` removes `CAP_SYS_MODULE`, so at boot the daemon
found no MSR device, logged `Error opening msr`, and gave up Dynamic Boost for the rest of its run:
it only tries at start. The test of the day before passed because the module, loaded earlier by
the unconfined daemon, was still present when the confined daemon restarted.

Resolution: the NVIDIA module loads `msr` at boot through `boot.kernelModules`, before any service
starts, and the daemon keeps its confinement.

## How to verify the fix

1. After a reboot on mains power, the module is loaded and the daemon logged no MSR error.

   ```bash
   lsmod | grep -w msr
   journalctl -b -u nvidia-powerd -o cat | grep -c 'Error opening msr'
   ```

   The second command prints `0`.

2. The current power limit is above the default limit.

   ```bash
   nvidia-smi -q -d POWER | grep -E 'Current Power Limit|Default Power Limit'
   ```

## Reference

| Source | Content |
| --- | --- |
| [msr(4)](https://man7.org/linux/man-pages/man4/msr.4.html) | The MSR device and the module that provides it |
| [systemd.exec ProtectKernelModules](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html) | Removal of `CAP_SYS_MODULE` and of the module directory |
