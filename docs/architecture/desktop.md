# Desktop

## Overview

The graphical session is KDE Plasma 6 on Wayland, started by the SDDM display manager, itself on
Wayland. The system side of the desktop is declared in `modules/desktop/plasma.nix`; the look and
the behaviour of Plasma are left to its own settings, stored in the persistent home.

### Session

SDDM runs its greeter in a Wayland compositor and starts the Plasma Wayland session. The keyboard
layout `fr` is declared for the greeter and the session; the virtual consoles use the `fr` keymap
as well.

`NIXOS_OZONE_WL=1` is set for every session. Electron and Chromium applications packaged by
nixpkgs read it and start with their native Wayland backend instead of XWayland, which gives sharp
rendering under fractional scaling.

The XDG desktop portals come from the Plasma module: file pickers, screen sharing and other
sandboxed requests go through the KDE portal implementation.

### Declared and mutable settings

The boundary between what is declared and what is left to Plasma follows one rule: the system
layer is declared, the appearance and the interactive behaviour of the desktop are not, until the
theme is declared as a whole.

| Area | Where it lives |
| --- | --- |
| Display manager, session type, keyboard layout, fonts installed | `modules/desktop/plasma.nix` |
| Applications installed | `home/mowsoon/desktop.nix`, Firefox in `plasma.nix` |
| Outbound rules of desktop components | `plasma.nix` and `hosts/hephaestus/opensnitch.nix` |
| Theme, wallpaper, panels, shortcuts, scaling | Plasma settings, `~/.config` |
| Lid switch, power key, sleep mode | Plasma energy settings (PowerDevil), `~/.config/powerdevilrc` |
| Region and format overrides for the session | Plasma region settings, `~/.config/plasma-localerc` |
| Application settings and presets | Each application, under `~/.config` or `~/.local/share` |

The home directory is persistent and snapshotted, so these settings survive reboots and can be
restored from a snapshot. A declared theme, applied to the desktop, the terminal, the editor and the
boot menu, is a Phase 7 subject of the migration roadmap.

### Fonts

JetBrains Mono from the Nerd Fonts set covers the terminal and the editor, including the glyphs of
the prompt. Noto covers text in most scripts, and Noto Color Emoji covers emoji.

### Desktop components on the network

Several Plasma components open outbound connections and carry their own OpenSnitch rules:
`plasmashell` for widgets such as weather, the KIO workers for remote files and downloads, Discover
and its notifier for update checks, and `fwupdmgr` when firmware updates are enabled. Their real
binaries are the `.<name>-wrapped` files behind the nixpkgs wrappers. The full list is in
[Network](network.md).

## How to find the file behind a Plasma setting

1. Change the setting in System Settings.
2. List the configuration files changed in the last minute.

   ```bash
   find ~/.config -maxdepth 1 -type f -mmin -1
   ```

3. Read the group and key that changed in the listed file. That file and key are what a future
   declaration has to set.

## How to reset a Plasma component to its defaults

1. Move its configuration file aside, for example the panels and widgets.

   ```bash
   mv ~/.config/plasma-org.kde.plasma.desktop-appletsrc ~/.config/plasma-org.kde.plasma.desktop-appletsrc.bak
   ```

2. Log out and log in again. Plasma recreates the file with its defaults.
3. Delete the `.bak` file once the result is satisfying, or move it back to undo.

## How to add a desktop application

1. Add the package to `home.packages` in `home/mowsoon/desktop.nix`.
2. Add its OpenSnitch rule to `hosts/hephaestus/opensnitch.nix`. The real binary of an Electron
   or Qt application is often a `.<name>-wrapped` file or a file under `lib/` or `opt/` of the
   package; find it as described in [Network](network.md).
3. If the package is unfree, add its name to `custom.unfreePackages` in `hosts/hephaestus/home.nix`.
4. Apply the configuration, then start the application from the launcher.

## Reference

### Session settings

| Setting | Value |
| --- | --- |
| `services.desktopManager.plasma6.enable` | `true` |
| `services.displayManager.sddm.enable` | `true` |
| `services.displayManager.sddm.wayland.enable` | `true` |
| `services.xserver.xkb.layout` | `fr` |
| `console.keyMap` | `fr` |
| `environment.sessionVariables.NIXOS_OZONE_WL` | `1` |
| `programs.firefox.enable` | `true` |

### Fonts

| Package | Coverage |
| --- | --- |
| `nerd-fonts.jetbrains-mono` | Monospace, prompt and editor glyphs |
| `noto-fonts` | Text in most scripts |
| `noto-fonts-color-emoji` | Colour emoji |

### Locale

| Setting | Value |
| --- | --- |
| `i18n.defaultLocale` | `en_US.UTF-8` |
| `LC_TIME`, `LC_PAPER`, `LC_MEASUREMENT` | `en_IE.UTF-8`: 24-hour clock, A4, metric units |
| `time.timeZone` | `Europe/Dublin` |

### Options

| Option | Default | Description |
| --- | --- | --- |
| `custom.plasma.enable` | `false` | Plasma 6, SDDM on Wayland, keyboard layout, fonts, Firefox, desktop OpenSnitch rules |

### Upstream documentation

| Subject | Link |
| --- | --- |
| KDE on NixOS | <https://wiki.nixos.org/wiki/KDE> |
| XDG desktop portals | <https://flatpak.github.io/xdg-desktop-portal/> |
| Stylix | <https://github.com/danth/stylix> |
| `services.desktopManager.plasma6` | <https://search.nixos.org/options?channel=unstable&query=services.desktopManager.plasma6> |
| `services.displayManager.sddm` | <https://search.nixos.org/options?channel=unstable&query=services.displayManager.sddm> |
| `fonts.packages` | <https://search.nixos.org/options?channel=unstable&query=fonts.packages> |
| `i18n.extraLocaleSettings` | <https://search.nixos.org/options?channel=unstable&query=i18n.extraLocaleSettings> |
