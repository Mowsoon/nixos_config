# Hibernation image dropped by the NVIDIA driver in the initrd

## Overview

On 2026-11-03, the first boot after a hibernation started a fresh session instead of restoring
the image. The image was complete: the initrd found it and read it in full, then the NVIDIA driver
refused to freeze and the kernel dropped the image:

```text
PM: Image successfully loaded
NVRM: GPU 0000:01:00.0: PreserveVideoMemoryAllocations module parameter is set. System Power Management attempted without driver procfs suspend interface. Please refer to the 'Configuring Power Management Support' section in the driver README.
nvidia 0000:01:00.0: PM: pci_pm_freeze(): nv_pmops_freeze [nvidia] returns -5
PM: hibernation: Failed to load image, recovering.
systemd-hibernate-resume: Unable to resume from device '/dev/disk/by-uuid/<uuid>' (254:0) offset <offset>, continuing boot process.
```

`<uuid>` and `<offset>` are the Btrfs file system and the swapfile offset.

Affected configuration:

| Component | Version |
| --- | --- |
| nixpkgs | `26.11.20261006.151fa4e` (`nixos-unstable`) |
| Kernel | `linuxPackages_zen`, 7.2.9 |
| NVIDIA driver | 595.104.02, open kernel modules, `kernelSuspendNotifier = false` |
| systemd | 261.3 |

Cause: since 2026-10-30, `nvidia`, `nvidia_modeset` and `nvidia_drm` were listed in
`boot.initrd.kernelModules` so the boot splash ran on the NVIDIA framebuffer. The driver was then
running in the initrd when `systemd-hibernate-resume` restored the image. Before jumping into the
image, the kernel freezes every device of the boot it is running. With
`NVreg_PreserveVideoMemoryAllocations=1` and without kernel suspend notifiers
([incident](hibernation-power-off.md)), the driver accepts a freeze only after
`/proc/driver/nvidia/suspend` has prepared it. In the running system `nvidia-hibernate.service`
does that; nothing does it in the initrd, so every resume failed. The last restored hibernation
dated from 2026-10-24, before the change; the sleeps in between never reached the hibernation
delay, so no resume ran through the new initrd.

Resolution: `modules/hardware/nvidia.nix` no longer loads the driver in the initrd. It loads after
the initrd, once the image has been restored or the boot goes on. The boot splash starts on
`simpledrm` and moves to `nvidia-drm` during the boot, and the initrd shrinks from about 124 MB to
about 31 MB compressed.

The same night, the laptop also stayed on after writing the image, with the screen black and the
fans running, on mains. That failure matches [hibernation-wakeup-hang](hibernation-wakeup-hang.md)
and is not related to the initrd: the image was written in full.

## How to verify the fix

1. Build and install the generation as the next boot entry.

   ```bash
   nixos-rebuild boot --flake ~/.config/nixos#hephaestus --elevate sudo
   ```

2. Reboot with `systemctl reboot`, never by resuming from hibernation.

3. Confirm the initrd no longer loads the driver: the first NVIDIA line of the boot must come
   after the switch to the real root.

   ```bash
   journalctl -b 0 -o short-precise | grep -m1 -E 'NVRM: loading|Switching root'
   ```

   ```text
   ... systemd[1]: Switching root.
   ```

4. Hibernate, wait for the machine to power off, then power it on. The session must come back.

   ```bash
   systemctl hibernate
   ```

5. Confirm the resume.

   ```bash
   journalctl -b 0 -k -g 'Image successfully loaded|hibernation exit|resume failed'
   ```

## Reference

| Source | Content |
| --- | --- |
| [NVIDIA 595.104.02 README, power management](https://download.nvidia.com/XFree86/Linux-x86_64/595.104.02/README/powermanagement.html) | `NVreg_PreserveVideoMemoryAllocations`, `/proc/driver/nvidia/suspend`, systemd units |
| [Arch Linux forums, early KMS and video memory preservation](https://bbs.archlinux.org/viewtopic.php?id=285508) | Same resume failure with the driver in the initramfs |
| [Linux kernel, swsusp](https://docs.kernel.org/power/swsusp.html) | Resume sequence from the boot kernel |
| [systemd-hibernate-resume.service(8)](https://www.freedesktop.org/software/systemd/man/latest/systemd-hibernate-resume.service.html) | Resume from the initrd |
