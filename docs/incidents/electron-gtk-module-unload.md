# Electron applications crash on a colour change

## Overview

From 2026-10-24, Discord crashed with `SIGSEGV` whenever Plasma changed its colours. Since the
accent colour follows the wallpaper, any new wallpaper was enough. Each crash came in the same
second as this line from `kded6`:

```text
xsettingsd: Reloading configuration
```

The core dumps showed a main thread stopped on an instruction pointer outside every loaded
module, in a mapped but non-executable page (`SEGV_ACCERR`), always at page offset `0x1b0`.

Affected configuration:

| Component | Version |
| --- | --- |
| Discord | 1.0.160, which bundles Electron 42.11.8 |
| Plasma | 6.7.5, `kde-gtk-config` 6.7.5 |
| GTK 3 | 3.24.52 |
| Session | Wayland, `accentColorFromWallpaper` enabled |

Cause: the Plasma GTK integration writes `gtk-modules=colorreload-gtk-module` to the user
`settings.ini` of GTK 3. The module watches `~/.config/gtk-3.0/colors.css` and reloads it when
Plasma rewrites it. Electron 41 to 45 carried a Chromium patch that sets `gtk-modules` to an empty
string after GTK has loaded the modules. GTK then unloads them, but the file monitor stays
connected. The next rewrite of `colors.css` calls the unloaded `reload_colours`, at offset
`0x11b0` of `libcolorreload-gtk-module.so`, which matches the page offset of every crash.
`window-decorations-gtk-module` has the same flaw with its own CSS file. Electron reverted the
patch in October 2026; an application gets the fix only once it bundles an Electron release that
contains the revert.

First resolution: `modules/desktop/plasma.nix` set `GTK_MODULES` to both modules for the session.
GTK keeps the modules named in the environment loaded even when the setting is emptied, and the
applications that do not use Electron loaded the same modules as before. GTK 4 ignores the
variable.

Current resolution: since the theme is declared through Stylix, the `gtkconfig` module of kded
is not loaded, and Home Manager writes the GTK `settings.ini` without `gtk-modules`. No GTK 3
application loads the two modules any more, and nothing rewrites `colors.css` during a session,
so the crash has no trigger left and `GTK_MODULES` was removed
([Desktop](../architecture/desktop.md#theme)).

The crash was reproduced by changing `AccentColor` in `kdeglobals` with `kwriteconfig6 --notify`
while Discord ran: Discord crashed within a second. With the two modules in `GTK_MODULES`, the
modules stayed mapped and the same change left Discord running.

After the Stylix change, on 2026-10-27, Discord ran without either module mapped and survived
an `AccentColor` change with `--notify`, two colour scheme changes with
`plasma-apply-colorscheme`, a write of `colors.css`, an atomic replacement of the `gtk.css` link
as a Home Manager activation does, and `plasma-apply-lookandfeel --apply stylix`.

Removing the variable took a reboot. NixOS passes session variables through `pam_env`, and the
systemd user manager keeps the environment it started with; it outlived the logout, and Plasma 6
starts `plasmashell` as one of its services, so the new session still inherited
`GTK_MODULES`. `systemctl --user unset-environment` does not remove a variable the manager
started with.

## How to verify the fix

1. Confirm that kded does not load `gtkconfig`. The command must print nothing.

   ```bash
   busctl --user call org.kde.kded6 /kded org.kde.kded6 loadedModules | tr ' ' '\n' | grep gtk
   ```

2. Start Discord and confirm neither module is mapped in its main process. The command must print
   nothing.

   ```bash
   grep -oE 'lib(colorreload|window-decorations)-gtk-module.so' /proc/$(pgrep -x -o .Discord-wrappe)/maps | sort -u
   ```

3. Change the colour scheme twice, then confirm no Discord crash was recorded. The last command
   must print nothing.

   ```bash
   plasma-apply-colorscheme BreezeDark
   plasma-apply-colorscheme Bordeaux
   coredumpctl list --since -10min --no-pager | grep -i discord
   ```

## Reference

| Source | Content |
| --- | --- |
| [electron/electron#54782](https://github.com/electron/electron/issues/54782) | Regression report: `gtk-modules` pinned to an empty string |
| [electron/electron#55015](https://github.com/electron/electron/pull/55015) | Revert on the 42 branch, merged on 2026-10-15 |
| [OpenWhispr#2780](https://github.com/OpenWhispr/openwhispr/issues/2780) | Same mechanism, isolated reproduction and the `GTK_MODULES` workaround |
| [microsoft/vscode#341708](https://github.com/microsoft/vscode/issues/341708) | Same crash in VS Code on a Plasma colour change |
| [GTK 3 running documentation](https://docs.gtk.org/gtk3/running.html) | `GTK_MODULES` and `GTK_PATH` |
