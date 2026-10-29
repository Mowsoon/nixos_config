# Home Manager activation blocked by the Plasma font settings

## Overview

On 2026-10-29, the settings declared through plasma-manager (window effects, title bar buttons,
border size) were missing from `~/.config/kwinrc` although the active generation contained them.
Every Home Manager activation since 2026-10-28 23:51 had failed before writing anything:

```text
hm-activate-mowsoon: Existing file '/home/mowsoon/.config/fontconfig/conf.d/10-hm-fonts.conf' would be clobbered
systemd: Failed to start Home Manager environment for mowsoon.
```

The switch itself reports success, so the failure only shows in the status of
`home-manager-mowsoon.service`.

Affected configuration:

| Component | Version |
| --- | --- |
| Plasma | 6.7.5, font settings page `kcm_fonts` |
| Home Manager | `fonts.fontconfig` writing `10-hm-fonts.conf` and `10-hm-rendering.conf` |

Cause: when the font settings page of Plasma saves, `KXftConfig` writes the rendering settings to
the first fontconfig file of the home directory that fontconfig loads, unless a `fonts.conf`
exists there. Without one, that file is `conf.d/10-hm-fonts.conf`, a link into the store, which
Plasma replaces with a regular file. Home Manager refuses to overwrite a regular file it did not
create and aborts the whole activation, so plasma-manager never runs. The same replacement had
happened on 2026-10-27.

Resolution: `modules/desktop/theme.nix` sets `force = true` on both Home Manager fontconfig files.
Home Manager now replaces them at every activation; a change saved in the font settings page
lasts until the next activation, and the declared rendering stays the only source.

## How to verify the fix

1. After a switch, confirm the Home Manager activation succeeded. The command must print
   `active`.

   ```bash
   systemctl is-active home-manager-mowsoon
   ```

2. Confirm the fontconfig files are links into the store. Both lines must show `->`.

   ```bash
   ls -l ~/.config/fontconfig/conf.d/10-hm-fonts.conf ~/.config/fontconfig/conf.d/10-hm-rendering.conf
   ```

## Reference

| Source | Content |
| --- | --- |
| `kcms/fonts/kxftconfig.cpp` in plasma-workspace | Choice of the file the font settings page writes |
| [Home Manager file options](https://nix-community.github.io/home-manager/options.xhtml) | `xdg.configFile.<name>.force` |
