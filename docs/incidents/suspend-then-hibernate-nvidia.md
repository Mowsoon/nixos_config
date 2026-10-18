# Suspend-then-hibernate refused by the NVIDIA driver

## Overview

On 2026-10-18, with the Plasma sleep mode set to "sleep, then hibernate", closing the lid or
running `systemctl suspend-then-hibernate` left the machine awake. The kernel logged that the
NVIDIA driver refused to suspend, and systemd-sleep gave up:

```text
nvidia 0000:01:00.0: PM: pci_pm_suspend(): nv_pmops_suspend [nvidia] returns -5
systemd-sleep: Failed to put system to sleep. System resumed again: Input/output error
```

Plain sleep (`systemctl suspend`) and plain hibernation worked.

Affected configuration:

| Component | Version |
| --- | --- |
| nixpkgs | `nixos-unstable`, October 2026 |
| NVIDIA driver | 595.104.02, open kernel modules, `kernelSuspendNotifier = false` |
| systemd | 261.3 |

Cause: with `kernelSuspendNotifier = false`
([incident](hibernation-power-off.md)), the driver accepts a sleep only after
`nvidia-sleep.sh` has prepared it through `/proc/driver/nvidia/suspend`. The nixpkgs NVIDIA module
runs that script before `systemd-suspend.service` and `systemd-hibernate.service` only. Nothing ran
before `systemd-suspend-then-hibernate.service`, so the driver returned an I/O error. The driver
also ships a `system-sleep` hook that switches it from sleep to hibernation when the delay
expires; NixOS does not install it.

Resolution: `modules/hardware/nvidia.nix` adds the unit NVIDIA ships on other distributions,
`nvidia-suspend-then-hibernate`, which runs `nvidia-sleep.sh suspend` before
`systemd-suspend-then-hibernate.service`, makes that service also pull in `nvidia-resume`, and
links the driver's hook to `/etc/systemd/system-sleep/nvidia`.

## How to verify the fix

1. Shorten the hibernation delay until the next reboot.

   ```bash
   sudo mkdir -p /run/systemd/sleep.conf.d && printf '[Sleep]\nHibernateDelaySec=2min\n' | sudo tee /run/systemd/sleep.conf.d/test.conf
   ```

2. Start a sleep, wait at least three minutes, then wake the machine. It must go through the
   firmware and the LUKS prompt.

   ```bash
   systemctl suspend-then-hibernate
   ```

3. Confirm the sleep turned into hibernation.

   ```bash
   journalctl -b -u systemd-suspend-then-hibernate.service -u nvidia-suspend-then-hibernate --no-pager
   ```

4. Remove the test delay.

   ```bash
   sudo rm /run/systemd/sleep.conf.d/test.conf
   ```

## Reference

| Source | Content |
| --- | --- |
| [NVIDIA 595.104.02 README, power management](https://download.nvidia.com/XFree86/Linux-x86_64/595.104.02/README/powermanagement.html) | systemd units and `system-sleep` hook shipped with the driver |
| [nixpkgs NVIDIA module](https://github.com/NixOS/nixpkgs/blob/nixos-unstable/nixos/modules/hardware/video/nvidia.nix) | Units generated for suspend and hibernation |
| [systemd-sleep(8)](https://www.freedesktop.org/software/systemd/man/latest/systemd-sleep.html) | `system-sleep` hooks and `SYSTEMD_SLEEP_ACTION` |
