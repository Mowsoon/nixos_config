# KWin errors while the session is inactive

## Overview

Since the installation, KWin logged two errors around every sleep and hibernation, and at
shutdown, in the user session and in the SDDM greeter:

```text
kwin_wayland: atomic commit failed: Permission denied
kwin_wayland: Applying output configuration failed!
```

The first came when the machine went to sleep, the second when it woke up and when the session
ended. The display always came back as configured; no failure was attached to either message. From
2026-10-17 to 2026-10-22, the journal holds 73 occurrences of the second message: 59 right after a
resume and 14 at shutdown, none during normal use.

Affected configuration:

| Component | Version |
| --- | --- |
| KWin | 6.7.5 |
| GPUs | NVIDIA RTX 4070 Laptop (`card1`, drives the panel) and AMD Radeon 610M (`card0`, no output) |
| Sleep path | `nvidia-sleep.sh` switches to virtual terminal 63 before sleep and back after resume |

Cause: both messages report a session that has lost the GPUs, a state KWin handles correctly.

- Before sleep, `nvidia-sleep.sh` switches to virtual terminal 63. logind revokes DRM master from
  the session before KWin receives the pause event, and a frame KWin submits in that window is
  rejected with `EACCES`. `src/backends/drm/drm_commit_thread.cpp` logs it as a warning.
- After resume, the switch back to the session lets logind resume the two GPUs one after the
  other. The first one triggers a new output configuration while the NVIDIA GPU, which drives the
  panel, is still inactive. The DRM backend answers `OutputConfigurationError::NotActive`.
  `Workspace::updateOutputConfiguration()` in `src/workspace.cpp` documents that case as expected
  ("have to wait for a VT switch") but still logs it at critical level. The second GPU resume
  applies the configuration.
- At shutdown, the session ends and loses the GPUs while KWin is still running, with the same
  `NotActive` answer.

Resolution: two patches in `pkgs/kwin/`, in `git format-patch` form against the KWin tree for a
later merge request to KDE, log those two cases at debug level and keep the other errors at their
level:

| Patch | Case moved to debug |
| --- | --- |
| `0001-workspace-don-t-log-a-critical-error-while-the-sessi.patch` | `updateOutputConfiguration()` ends on `NotActive` |
| `0002-backends-drm-don-t-warn-about-commits-rejected-after.patch` | An atomic commit fails with `EACCES`, which only means the caller is not the DRM master |

`modules/desktop/plasma.nix` builds KWin with the patches and substitutes it in the system closure
through `system.replaceDependencies`. Only KWin is compiled: the packages that depend on it keep
their cached builds, and their references to KWin are rewritten to the patched build. The patches
carry no `Signed-off-by` line; KDE does not require one.

`KWIN_DRM_DEVICES` is left unset. Restricting KWin to the NVIDIA GPU would remove the race at
resume, but not the shutdown case, and would hide the integrated GPU from the compositor.

## How to verify the fix

1. Confirm the running system is the latest generation. Both paths must be identical.

   ```bash
   readlink -f /run/booted-system /nix/var/nix/profiles/system
   ```

2. Sleep, wait a few seconds, then wake the machine.

   ```bash
   systemctl suspend
   ```

3. Confirm neither message was logged since the boot. The command must print nothing.

   ```bash
   journalctl -b 0 | grep -E 'Applying output configuration failed|atomic commit failed: Permission denied'
   ```

If the output configuration message still appears after a resume, the failure was not `NotActive`
and is a real configuration error to investigate.

## How to check whether the patches are still needed

Run this after a Plasma update.

1. Build the system. If a patch no longer applies, the KWin build fails at its patch phase.

   ```bash
   nix build ~/.config/nixos#nixosConfigurations.hephaestus.config.system.build.toplevel
   ```

2. If the new KWin source already logs `NotActive` and `EACCES` at debug level, remove the
   patches from `modules/desktop/plasma.nix` and delete `pkgs/kwin/`. Otherwise port them to the
   new source and regenerate them with `git format-patch`.

## Reference

| Source | Content |
| --- | --- |
| [KWin repository](https://invent.kde.org/plasma/kwin) | Source, merge requests |
| [KDE commit policy](https://community.kde.org/Policies/Commit_Policy) | Commit message conventions |
| [NixOS options search](https://search.nixos.org/options?channel=unstable&query=system.replaceDependencies) | `system.replaceDependencies.replacements` |
| [NVIDIA forum report](https://forums.developer.nvidia.com/t/kwin-wayland-applying-output-configuration-failed-failed-to-open-drm-node-permission-denied-on-every-s3-resume-optimus-rtx-3070-ti-laptop-gpu/377906) | Same message on another NVIDIA laptop with two GPUs |
| [systemd-logind D-Bus interface](https://www.freedesktop.org/software/systemd/man/latest/org.freedesktop.login1.html) | `PauseDevice`, `ResumeDevice`, DRM master handling |
