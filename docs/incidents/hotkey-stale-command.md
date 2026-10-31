# G keys run the command of an older generation

## Overview

On 2026-10-30, G2 and G3 opened Neovim on an error instead of the file:

```text
E5113: Lua chunk: /home/mowsoon/.config/nvim/init.lua:0: module 'catppuccin' not found
```

`nvim` started from a terminal loaded the colour scheme without error. The session had started
at 20:44 and the last switch, which replaced rose-pine with catppuccin, ran at 21:47.

Affected configuration:

| Component | Version |
| --- | --- |
| Plasma | 6, kglobalaccel loaded inside `kwin_wayland` |
| plasma-manager | `programs.plasma.hotkeys.commands`, one hidden desktop entry with one action per command |

Cause: kglobalaccel reads the `Exec` line of each desktop action when the session starts and keeps
it in memory until the session ends; it does not reload it when the service cache is rebuilt. The
command held store paths, so after the switch the G keys still ran the Neovim of the previous
generation, whose plugin directory had no catppuccin, while the `init.lua` linked in
`~/.config/nvim` came from the new generation. Triggering G2 over D-Bus started
`/nix/store/<hash>-nixvim/bin/nvim` with the hash of the previous generation. Every command bound
to a G key had the same flaw; the others only failed silently, by running an older script or
showing an older alias list.

Resolution: `home/mowsoon/shortcuts.nix` installs each G key command as a script of the user
profile, named after the command, and binds the key to
`/etc/profiles/per-user/mowsoon/bin/<command>`. That path never changes, and each switch points it
to the script of the new generation, so the line kept by kglobalaccel stays valid. Only a new or
rebound key still needs a new session.

## How to verify the fix

1. After the first login that follows the switch, trigger G2 over D-Bus, then list the processes
   it started. The `nvim` wrapper must be the one of the current profile.

   ```bash
   qdbus org.kde.kglobalaccel /component/plasma_manager_commands_desktop \
     org.kde.kglobalaccel.Component.invokeShortcut show-editor-keymaps
   pgrep -af editor-keymaps
   ```

2. Change the editor, switch, and press G2 again without logging out. Neovim must start without
   error.

## Reference

| Source | Content |
| --- | --- |
| [plasma-manager hotkeys](https://github.com/nix-community/plasma-manager/blob/trunk/modules/hotkeys.nix) | How the commands become actions of one desktop entry |
| [KGlobalAccel](https://api.kde.org/frameworks/kglobalaccel/html/index.html) | Global shortcut service of KDE Frameworks |
