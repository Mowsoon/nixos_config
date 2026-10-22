# MT7921 Wi-Fi restore error after hibernation

## Overview

Every resume from hibernation logged a timeout of the Wi-Fi driver, then a failed restore:

```text
mt7921e 0000:04:00.0: Message 00020007 (seq 9) timeout
mt7921e 0000:04:00.0: PM: dpm_run_callback(): pci_pm_restore returns -110
mt7921e 0000:04:00.0: PM: failed to restore async: error -110
```

The driver then reset the chip, reloaded its firmware and Wi-Fi reconnected. Resume took about
three seconds longer. No other effect was observed: unloading the driver before hibernating did not
change [hibernation-power-off](hibernation-power-off.md) nor the failed wake-up after a resume from
hibernation.

Affected configuration:

| Component | Version |
| --- | --- |
| Wi-Fi chip | MediaTek MT7922 (`ASIC revision: 79220010`) |
| Driver | `mt7921e`, in-tree mt76 of `linuxPackages_zen` 7.2.9 |
| Firmware | Build 20260724 from `linux-firmware` |

Cause: the driver registers one function for both resume from sleep and restore from hibernation
(`DEFINE_SIMPLE_DEV_PM_OPS` in `mt7921/pci.c`). After sleep, the chip kept its power and its
firmware runs, so the function sends the `HIF_CTRL` command (unified command `0x07`, logged as
`00020007`) to tell the firmware the host is back. After hibernation, the chip was powered off and
no firmware runs: the command waits three seconds for an answer that never comes, fails with
`-ETIMEDOUT` (`-110`), and the error path resets the chip. The error has been reported since 2023
in kernel bug 217415. The sibling driver mt7925 received a dedicated restore callback in
September 2025; mt7921 did not, up to kernel 7.2.9.

Resolution: `pkgs/mt76/0001-wifi-mt76-mt7921-add-pci-restore-for-hibernate.patch` ports the mt7925
change to mt7921. On restore, the driver skips the firmware command and resets the chip directly.
`pkgs/mt76/package.nix` rebuilds only `drivers/net/wireless/mediatek/mt76` from the kernel source,
against the `dev` output of the cached kernel, so the kernel itself is not rebuilt. The modules are
installed under `updates/`, which `depmod` searches before the in-tree modules, and the whole mt76
directory is rebuilt so that the core library and the chip drivers always come from the same build.
`modules/hardware/mt7921.nix` adds the package to `boot.extraModulePackages`.

The patch is in `git format-patch` form, against the kernel tree root, for a later submission to
the mt76 maintainers. It carries no `Signed-off-by` line: the submitter adds it with their own
identity.

The rebuilt modules are not signed. The kernel loads them because it does not enforce module
signatures, which the NVIDIA modules already rely on.

## How to verify the fix

1. Confirm the running system is the latest generation. Both paths must be identical.

   ```bash
   readlink -f /run/booted-system /nix/var/nix/profiles/system
   ```

2. Confirm the loaded driver comes from the rebuilt package.

   ```bash
   modinfo -F filename mt7921e
   ```

   The path must contain `/updates/mt7921/`.

3. Hibernate and power on.

   ```bash
   systemctl hibernate
   ```

4. Confirm the resume logged no restore error. The command must print nothing.

   ```bash
   journalctl -b 0 -k | grep 'pci_pm_restore returns'
   ```

## How to check whether the patch is still needed

Run this after a kernel update.

1. Look for a restore callback in the in-tree driver of the new kernel.

   ```bash
   grep -n 'restore' "$(nix build --no-link --print-out-paths ~/.config/nixos#nixosConfigurations.hephaestus.config.boot.kernelPackages.kernel.src)/drivers/net/wireless/mediatek/mt76/mt7921/pci.c"
   ```

2. If the file defines `mt7921_pci_restore`, the fix is upstream: remove `custom.mt7921.enable`
   from `hosts/hephaestus/hardware.nix`, then delete `modules/hardware/mt7921.nix` and
   `pkgs/mt76/`.
3. If the patch no longer applies, the package build fails at its patch phase. Port it again on the
   new `mt7921/pci.c` and regenerate it with `git format-patch`.

## Reference

| Source | Content |
| --- | --- |
| [Kernel bug 217415](https://bugzilla.kernel.org/show_bug.cgi?id=217415) | Same three lines on resume from hibernation |
| [mt7925 restore patch](https://lkml.iu.edu/2510.3/01925.html) | Commit `d54424fbc53b`, "wifi: mt76: mt7925: add pci restore for hibernate" |
| [Linux kernel, building external modules](https://docs.kernel.org/kbuild/modules.html) | `M=`, `modules_install`, `INSTALL_MOD_DIR` |
| [Linux kernel, device power management](https://docs.kernel.org/driver-api/pm/devices.html) | `freeze`, `thaw`, `poweroff` and `restore` callbacks |
| [depmod.d(5)](https://man7.org/linux/man-pages/man5/depmod.d.5.html) | Search order of `updates` and in-tree modules |
| [Submitting patches](https://docs.kernel.org/process/submitting-patches.html) | `Signed-off-by`, `git format-patch`, mailing list submission |
