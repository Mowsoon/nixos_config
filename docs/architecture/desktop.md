# Desktop

## Overview

The graphical session is KDE Plasma 6 on Wayland, started by the SDDM display manager, itself on
Wayland. The system side of the desktop is declared in `modules/desktop/plasma.nix`; the look and
the behaviour of Plasma are left to its own settings, stored in the persistent home.

### Session

SDDM runs its greeter in a Wayland compositor and starts the Plasma Wayland session. The keyboard
layout `fr` is declared for the greeter and the session; the virtual consoles use the `fr` keymap
as well.

Every login starts an empty session. Plasma would otherwise relaunch the applications open at the
previous logout, through ksmserver for the applications that support session management and
through `plasma-fallback-session-restore` for the others. Both read `loginMode` in the `General`
group of `ksmserverrc`; the Plasma module sets it to `emptySession` in `/etc/xdg/ksmserverrc` and
marks it immutable with `[$i]`, so neither the user file nor the Plasma settings can change it.

`NIXOS_OZONE_WL=1` is set for every session. Electron and Chromium applications packaged by
nixpkgs read it and start with their native Wayland backend instead of XWayland, which gives sharp
rendering under fractional scaling.

The XDG desktop portals come from the Plasma module: file pickers, screen sharing and other
sandboxed requests go through the KDE portal implementation.

KWin carries two patches from `pkgs/kwin/`. They lower to debug level the errors it logs when the
session has lost the GPUs, which happens at every sleep, resume and shutdown because
`nvidia-sleep.sh` switches virtual terminals. The patched KWin replaces the packaged one through
`system.replaceDependencies`, so only KWin is compiled
([incident](../incidents/kwin-inactive-session-errors.md)).

### Declared and mutable settings

The boundary between what is declared and what is left to Plasma follows one rule: the system
layer is declared, the appearance and the interactive behaviour of the desktop are not, until the
theme is declared. Theming is declared in two parts: the settings of each application first, then
the display (palette, wallpaper, fonts applied everywhere).

| Area | Where it lives |
| --- | --- |
| Display manager, session type, session restore, keyboard layout, fonts installed | `modules/desktop/plasma.nix` |
| Applications installed | `home/mowsoon/desktop.nix`, Firefox in `firefox.nix` |
| Firefox settings, extensions, search engine | `modules/desktop/firefox.nix` |
| Default applications per file type | `home/mowsoon/mime.nix` |
| Outbound rules of desktop components | `plasma.nix` and `hosts/hephaestus/opensnitch.nix` |
| Theme, wallpaper, panels, shortcuts, scaling | Plasma settings, `~/.config` |
| Lid switch, power key, sleep mode | Plasma energy settings (PowerDevil), `~/.config/powerdevilrc` |
| Region and format overrides for the session | Plasma region settings, `~/.config/plasma-localerc` |
| Settings of the applications not yet declared | Each application, under `~/.config` or `~/.local/share` |

The home directory is persistent and snapshotted, so these settings survive reboots and can be
restored from a snapshot. The display part of the theme, applied to the desktop, the terminal, the
editor and the boot menu, is a Phase 7 subject of the migration roadmap.

### Firefox

Firefox is configured through its enterprise policies. NixOS writes them to
`/etc/firefox/policies/policies.json`, which Firefox reads at every start, for every profile. A
setting declared there cannot be changed from the interface; this is why Firefox reports that it is
managed by an organisation. Preferences from `about:config` are passed through the same file and
are locked.

The profile itself stays mutable in the persistent home: history, cookies, open tabs and the
Bitwarden session live there and are not declared.

- Tracking protection is locked on the strict category, and Global Privacy Control is sent.
- DNS over HTTPS is disabled and locked, so every lookup goes through systemd-resolved and Quad9
  over TLS, like the rest of the system.
- HTTPS-First upgrades every connection that supports it and falls back to HTTP otherwise.
  HTTPS-Only stays off because it also upgrades local development host names.
- Bitwarden replaces the built-in password manager and form autofill, which are disabled to avoid
  two concurrent vaults.
- uBlock Origin and Bitwarden are force-installed from addons.mozilla.org at their latest version.
  They update themselves and are not pinned by the flake, which keeps security fixes flowing.
- The uBlock Origin filter lists are set through the extension managed storage. The declared list
  replaces the whole local selection; the "My filters" pane stays available.
- uBlock Origin runs in medium mode: third-party scripts and frames are blocked on every site. A
  site that needs one gets a `noop` rule for that third-party host on that site only. A `noop`
  rule lifts the medium-mode block alone, so the filter lists keep blocking trackers served by the
  allowed host.
- The per-site allowances name the sites the user visits, so they live in the private input
  described in [Architecture overview](overview.md#private-input), not in this repository.
- uBlock Origin evaluates dynamic rules only in advanced user mode, which is declared on as well.
  It also shows the per-host cells used to set `noop` rules in the popup.
- The dynamic rules ("My rules") are declared and overwrite the local ones at every Firefox start.
  A rule saved with the padlock in the popup is lost at the next start; a fix becomes permanent
  only once declared.
- DuckDuckGo is the default search engine, in normal and private windows.
- Telemetry, studies, sponsored shortcuts, stories and suggestions are disabled.

The Firefox theme belongs to the display part of theming and is not declared yet.

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

## How to find the applications running through XWayland

1. Open the applications to check.
2. List the X11 clients connected to XWayland.

   ```bash
   nix shell nixpkgs#xlsclients -c xlsclients -l
   ```

3. Any application listed renders through XWayland and is blurry under fractional scaling. An
   empty list means every open application is a native Wayland client.

## How to check the policies applied to Firefox

1. Open `about:policies` in Firefox.
2. Read the Active tab. A policy listed in the Errors tab was rejected, usually because of a wrong
   key or value type.

## How to add a Firefox extension

1. Install the extension once from addons.mozilla.org.
2. Open `about:support` and read its ID in the Add-ons table.
3. Read the slug of its addons.mozilla.org page: the last segment of
   `https://addons.mozilla.org/firefox/addon/<slug>/`.
4. Add the ID and the slug to `ExtensionSettings` in `modules/desktop/firefox.nix`.

   ```nix
   {
     programs.firefox.policies.ExtensionSettings."<id>" = {
       installation_mode = "force_installed";
       install_url = "https://addons.mozilla.org/firefox/downloads/latest/<slug>/latest.xpi";
     };
   }
   ```

   `<id>` is the ID read in `about:support`, `<slug>` the slug of the addons.mozilla.org page.

5. Apply the configuration and restart Firefox.

## How to allow a third party on a site broken by medium mode

1. On the broken page, open the uBlock Origin popup and expand the per-host list.
2. Set the blocked third-party host to `noop` (the grey cell) for this site, without clicking the
   padlock: the rule lasts for the session only.
3. Reload the page. Repeat for the next host until the page works, keeping the fewest hosts.
4. Add the hosts to `firefox/ublock-allowances.nix` in the clone of the private repository,
   keyed by the site. The sites a user visits are personal data: they never go into this public
   repository, its documentation or its commit messages.

   ```nix
   {
     "<site>" = [
       "<host>"
     ];
   }
   ```

   `<site>` is the registrable domain of the visited site, `<host>` the registrable domain of the
   third party set to `noop`.

5. Commit and push the private repository, then move the pinned revision of the input in this
   repository. The input is fetched over SSH with the key of the user, so this runs without
   `sudo`.

   ```bash
   nix flake update nixos-private
   ```

6. Apply the configuration and restart Firefox twice. uBlock Origin reads its cached copy of the
   managed settings at start and refreshes the cache afterwards, so new rules apply from the
   second start.

When the blocked hosts are not obvious, the built-in browser of the Claude desktop app, which runs
without uBlock Origin, lists every script and frame a page loads. The third-party ones that are
not advertising or tracking are the hosts to allow.

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
| `loginMode` in `/etc/xdg/ksmserverrc` | `emptySession`, immutable |
| `system.replaceDependencies.replacements` | `kdePackages.kwin` with the patches of `pkgs/kwin/` |

### Firefox

| Setting | Mechanism | Value |
| --- | --- | --- |
| Tracking protection | `EnableTrackingProtection` policy | `strict`, locked |
| Global Privacy Control | `privacy.globalprivacycontrol.enabled` | `true` |
| HTTPS-First | `dom.security.https_first` | `true` |
| DNS over HTTPS | `DNSOverHTTPS` policy | Disabled, locked |
| WebRTC local addresses | `media.peerconnection.ice.default_address_only` | `true` |
| Internationalised domain names | `network.IDN_show_punycode` | Shown as punycode |
| Password manager, address and card autofill | Policies | Disabled |
| Telemetry, studies | Policies | Disabled |
| Sponsored content | `FirefoxHome`, `FirefoxSuggest` policies | Disabled |
| Default search engine | `SearchEngines` policy | DuckDuckGo |
| Hardware video decoding | `media.hardware-video-decoding.force-enabled`, set by `hardware/nvidia.nix` | `true` |
| Preferences status | `programs.firefox.preferencesStatus` | `locked` |

| Extension | ID | Installation |
| --- | --- | --- |
| uBlock Origin | `uBlock0@raymondhill.net` | Forced, latest from AMO, private windows, toolbar |
| Bitwarden | `{446900e4-71c2-419f-a6a7-df9c091e268b}` | Forced, latest from AMO, private windows, toolbar |

| uBlock Origin dynamic rules | Effect |
| --- | --- |
| `behind-the-scene * ... noop` | uBlock Origin defaults, kept because the declared set replaces all rules |
| `* * 3p-script block` | Third-party scripts blocked everywhere |
| `* * 3p-frame block` | Third-party frames blocked everywhere |
| `<site> <host> * noop` | One per entry of `firefox/ublock-allowances.nix` in the private input |

| uBlock Origin filter lists | Tokens |
| --- | --- |
| Stock defaults | `user-filters`, `ublock-filters`, `ublock-badware`, `ublock-privacy`, `ublock-unbreak`, `ublock-quick-fixes`, `easylist`, `easyprivacy`, `urlhaus-1`, `plowe-0` |
| Added | `adguard-spyware-url` (tracking parameters), `block-lan` (public sites reaching the LAN), `curben-phishing` |

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
| `custom.plasma.enable` | `false` | Plasma 6, SDDM on Wayland, keyboard layout, fonts, desktop OpenSnitch rules |
| `custom.firefox.enable` | `false` | Firefox with its policies, extensions and OpenSnitch rule |

### Upstream documentation

| Subject | Link |
| --- | --- |
| KDE on NixOS | <https://wiki.nixos.org/wiki/KDE> |
| XDG desktop portals | <https://flatpak.github.io/xdg-desktop-portal/> |
| Stylix | <https://github.com/danth/stylix> |
| Firefox policies | <https://mozilla.github.io/enterprise-admin-reference/reference/policies/> |
| uBlock Origin managed settings | <https://github.com/gorhill/uBlock/wiki/Deploying-uBlock-Origin:-configuration> |
| uBlock Origin medium mode | <https://github.com/gorhill/uBlock/wiki/Blocking-mode:-medium-mode> |
| `programs.firefox` | <https://search.nixos.org/options?channel=unstable&query=programs.firefox> |
| `services.desktopManager.plasma6` | <https://search.nixos.org/options?channel=unstable&query=services.desktopManager.plasma6> |
| `services.displayManager.sddm` | <https://search.nixos.org/options?channel=unstable&query=services.displayManager.sddm> |
| `fonts.packages` | <https://search.nixos.org/options?channel=unstable&query=fonts.packages> |
| `i18n.extraLocaleSettings` | <https://search.nixos.org/options?channel=unstable&query=i18n.extraLocaleSettings> |
