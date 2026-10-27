# Desktop scripts of plasma-manager run before plasmashell

## Overview

On 2026-10-27, the first login after the panel and the wallpaper were declared came back with the
default Plasma layout: one panel at the bottom and the default wallpaper on the desktop. The lock
screen showed the declared wallpaper, because it is a configuration key that Home Manager writes
at activation.

The journal of the session showed both desktop scripts failing three seconds before
`plasmashell` started:

```text
run_all.sh: Running script: desktop_script_panels
run_all.sh: Cannot find 'org.kde.PlasmaShell.evaluateScript' in object /PlasmaShell at org.kde.plasmashell
```

Affected configuration:

| Component | Version |
| --- | --- |
| Plasma | 6.7.5, `plasmashell` started as a systemd user service |
| plasma-manager | Autostart entry `plasma-manager-autostart.desktop`, condition `ksmserver` |

Cause: plasma-manager runs its startup and desktop scripts from one autostart entry. The desktop
scripts call `evaluateScript` of `plasmashell` over D-Bus, but nothing makes the autostart entry
wait for `plasmashell`, which starts as its own user service. The panel script deletes
`~/.config/plasma-org.kde.plasma.desktop-appletsrc` before calling `plasmashell`, so the failed
call left no layout at all, and `plasmashell` then started on the defaults. A failed script is
not recorded as done, so it runs again at the next login, with the same race.

Resolution: `modules/desktop/theme.nix` adds a startup script of priority 0,
`wait_for_plasmashell`, run at every login. The runner executes the scripts in the order of their
file names, so it runs before the desktop scripts and waits, up to two minutes, until
`plasmashell` exposes `evaluateScript`.

## How to verify the fix

1. Log out and log in again, then read the scripts run by plasma-manager in this session. The
   wait must come before the desktop scripts, and no `Cannot find` line may appear.

   ```bash
   journalctl --user -b -t run_all.sh --no-pager
   ```

2. Confirm the declared wallpaper is on the desktop containment. The command must print a path
   in `/nix/store`.

   ```bash
   grep '^Image=' ~/.config/plasma-org.kde.plasma.desktop-appletsrc
   ```

## Reference

| Source | Content |
| --- | --- |
| [plasma-manager#76](https://github.com/nix-community/plasma-manager/issues/76) | Why the panel script deletes the layout file before running |
| [Plasma desktop scripting](https://develop.kde.org/docs/plasma/scripting/) | `evaluateScript` and the scripting API of `plasmashell` |
