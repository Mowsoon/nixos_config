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

The accent colour follows the wallpaper. Plasma computes it from the wallpaper and writes it to
`AccentColor` in the user `kdeglobals`; the switch that enables it, `accentColorFromWallpaper` in
the `General` group, is declared in `/etc/xdg/kdeglobals` and marked immutable the same way. The
keyboard lighting effects read the resulting accent as one of their master hues.

After every resume from hibernation, a service kills the lock screen greeter, which the screen
locker restarts at once: the greeter carried through hibernation makes the next sleep hang
([incident](../incidents/sleep-after-hibernation-deadlock.md)).

`NIXOS_OZONE_WL=1` is set for every session. Electron and Chromium applications packaged by
nixpkgs read it and start with their native Wayland backend instead of XWayland, which gives sharp
rendering under fractional scaling.

`GTK_MODULES` names the two GTK 3 modules of the Plasma GTK integration,
`colorreload-gtk-module` and `window-decorations-gtk-module`, which the user `settings.ini` of
GTK 3 already loads in every GTK 3 application. Loaded from the environment, they stay in memory
in Electron applications whose Electron empties the `gtk-modules` setting at start: unloaded, they
make the application crash at the next colour change, such as a new wallpaper accent
([incident](../incidents/electron-gtk-module-unload.md)).

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
| Display manager, session type, session restore, accent from wallpaper, keyboard layout, fonts installed | `modules/desktop/plasma.nix` |
| Applications installed | `home/mowsoon/desktop.nix`, Firefox in `firefox.nix` |
| Firefox settings, extensions, search engine | `modules/desktop/firefox.nix` |
| Default applications per file type | `home/mowsoon/mime.nix` |
| Outbound rules of desktop components | `plasma.nix` and `hosts/hephaestus/opensnitch.nix` |
| KRunner shortcuts, commands of the G keys | `home/mowsoon/shortcuts.nix`, through plasma-manager |
| Theme, wallpaper, panels, other shortcuts, scaling | Plasma settings, `~/.config` |
| Lid switch, power key, sleep mode | Plasma energy settings (PowerDevil), `~/.config/powerdevilrc` |
| Region and format overrides for the session | Plasma region settings, `~/.config/plasma-localerc` |
| Settings of the applications not yet declared | Each application, under `~/.config` or `~/.local/share` |

The home directory is persistent and snapshotted, so these settings survive reboots and can be
restored from a snapshot. The display part of the theme, applied to the desktop, the terminal, the
editor and the boot menu, is a Phase 7 subject of the migration roadmap.

### Global shortcuts

plasma-manager writes the declared shortcuts into `~/.config/kglobalshortcutsrc` and leaves every
other entry of the file untouched (`overrideConfig` stays off), so the shortcuts set in the Plasma
settings coexist with the declared ones. A declared entry overwrites a change made to it in the
settings at the next activation. KRunner keeps its default shortcuts and gains Meta+Space.

Each G key of the G915 X reaches Plasma as a dedicated key symbol, set in
[Hardware](hardware.md). A command is bound to that symbol through
`programs.plasma.hotkeys.commands`, which generates one hidden desktop entry whose actions are the
commands; kglobalaccel starts the action, and its output goes to the journal. A new or changed
binding is read by kglobalaccel at the next login.

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

### Keyboard lighting effects

The effects of the Logitech G915 X are a Python daemon of this repository, `pkgs/rgb-effects`,
run as a user service of the graphical session and configured only through Nix options of
`modules/desktop/rgb-effects.nix`; no profile saved from the OpenRGB interface is a source of
truth. The daemon needs the OpenRGB SDK server of `custom.rgb`, described in
[Hardware](hardware.md#lighting). It is an SDK client of the local server. On every connection it
sends a frame that differs from the target on every LED, then the target, so the server rewrites
the whole keyboard buffer. It retries with an exponential delay while the
server or the keyboard is missing. Its sandbox cannot filter IP addresses, which a user manager
cannot do; OpenSnitch denies any destination other than the loopback.

The package splits its code by responsibility. `sdk` talks to the OpenRGB server, `dbus` holds
the session bus interface and the commands that call it, `sources` produces events (keys, sound,
screen, notifications, power, accent colour), `effects` turns them into layers, one module per
effect, and `render` composes the layers into the frame that fits the radio. The boundary between
`sources` and `effects` is also the security boundary: the key reader lives alone in
`sources/keys/reader.py`, imports nothing from the package, which a test enforces, and only a key
code leaves it. The tests, the linter and the type checker run in `nix flake check`.

Every frame goes through one pipeline over the 6 by 21 key matrix, held in float32 arrays.

1. The palette is synthesised from the inputs: the master hues are the colour of the focused
   application and the Plasma accent colour; the time-of-day schedule sets the brightness ceiling
   and warms every colour towards its own hue, amber at night.
2. The background is a gradient noise field flowing through the master hues; it flows faster
   while keys are pressed. After the idle delay without a key press it fades into the Brian's
   Brain cellular automaton, stepped three times per second, and fades back on the next press.
3. The physical layer adds what typing produces, as fields over the same matrix. Every press raises
   a slow heat map, which diffuses to the neighbouring keys and decays over minutes. The pressed key
   glows from white to dark red; it cools in 0.8 s on a cold key and up to 2.5 s on the hottest,
   where a faint halo stays. Every press also starts a damped 2D wave, which travels further where
   the heat map is hot and always settles back to rest; a key lights only where the crest of the
   wave passes. Below the sand typing speed, the press also drops a grain that falls one row at a
   time and piles up on the bottom row; Enter clears the pile and sweeps a wave along that row. This
   layer has its own brightness ceiling, so presses stay visible when the time-of-day ceiling is
   low.
4. The HUD overrides the keys it uses. While Ctrl, Alt or Super is held, every other key is
   dimmed and the keys bound to that combination light in the colour of their category. A focus
   timer started with `rgb-focus` turns F1 to F12 into a progress bar and blinks it when the time
   is up. Holding Right Ctrl alone shows a binary clock: hours on F1 to F5, minutes on the number
   row from `&` to `-`, most significant bit first.
5. The frame is quantised, in the OKLab colour space, to a table of six to eight colours, with a
   hysteresis so a key changes colour only when the new colour is clearly closer.
6. A budget pass compares the colours with those sent in the previous frame, computes the exact
   packet cost of the differences with the grouping rules of OpenRGB, and keeps those that fit the
   per-frame share of the packet ceiling, by priority (HUD keys, then pressed keys) and by error;
   the other keys keep the colour already sent and wait for the next frame.

The LEDs outside the matrix follow it: the G keys take the left column, the media keys the top
right cell, and the logo the primary hue. The daemon animates at the configured frame rate while
keys have been pressed within the sleep delay, or a modifier is held, or a focus timer runs, and
recomputes once per refresh interval otherwise. While awake it hands every frame to OpenRGB even
when nothing changed: OpenRGB resends the keys whose packets the keyboard did not acknowledge only
when it receives a frame, and sends nothing over the radio when every key is committed.

The hue of the background follows the focused application without any screen capture. At start
the daemon owns the session bus name `org.hephaestus.RgbEffects` and loads a KWin script through
`org.kde.kwin.Scripting`, without writing to the Plasma configuration; the script calls the daemon
on every window activation with the application identifier only, never the window title, which
can hold personal data. An application listed in the colour table gives the primary hue; any
other application gives back the schedule colour. The script is
unloaded when the daemon stops, and lost if KWin restarts, until the daemon restarts too.

Key-reactive effects read the keyboard through a separate system service, `rgb-keyreader`, so the
daemon never holds the input device. The reader starts only when the daemon connects to its socket,
reads the evdev node of the G915 X, a link `/dev/input/g915x-keyboard` that a udev rule gives to the
`rgb-keys` group in read-only mode, and forwards one packet per key press: the key code, or in pulse
mode only the fact that a key was pressed. It also forwards the release of the six modifier keys
(Ctrl, Alt and Super on both sides), and ignores every other release, the repeats and every other
event; it keeps no history, logs no key and has no network. It does not grab the device, so Plasma
receives every key as before. The daemon maps a key code to the LED at the same physical position,
where the physical layer makes it glow.

Sound-reactive effects read what the computer plays. The daemon runs `pw-record` on the monitor of
the default PipeWire sink (`stream.capture.sink`) with `node.dont-move` set, so neither WirePlumber
nor EasyEffects, which moves recording streams to its microphone source, can reroute it to a
microphone; the stream is named `rgb-effects-monitor`. Each block of 1024 samples gives the level of
both channels and 21 logarithmic bands from 40 Hz to 16 kHz, one per matrix column, measured against
a slowly decaying peak over 50 dB. Nothing else is kept. Each band lights its column from the bottom
row in the sound colour, at the brightness ceiling of the key-reactive layer so it stays visible at
night; a key is either lit or left to the background, which keeps the quantised table stable. The
stereo balance tilts the columns sideways, and the level speeds up the flow. A sharp attack, found
by spectral flux above an adaptive threshold, starts a circular wave from the centre of the keyboard
in the solver of the physical layer. A 12-note chromagram, smoothed over a few seconds and read on
the circle of fifths, slowly turns the master hues within the hue range, so the background follows
the harmony of the piece. While sound plays the daemon stays awake and the automaton stays away;
after the silence delay the audio gains fade back to nothing over two seconds.

Desktop notifications send a plane wave from both side edges towards the centre, in the colour of
the sending application from the window colour table, or of the accent for an unknown one. Plasma
offers no interface to observe notifications, so a separate user service, `rgb-notifywatch`, becomes
a monitor of the session bus restricted to the `Notify` calls. It keeps only the application name,
which it passes to the daemon through `NotificationShown`; the title and the text it receives are
dropped at once and never logged. It runs in a private network namespace with Unix sockets only,
sees no home directory and, of the runtime directory, only the session bus socket, and writes
nowhere.

The screen is read only while a window is in full screen, the case of a film or a game. The KWin
script also reports whether the focused window is in full screen; the daemon then opens a session of
the ScreenCast portal of the desktop for one monitor, with `persist_mode` 2 so that the consent
given once is restored without a dialog. The restore token is kept in
`~/.local/state/rgb-effects/screencast-token`, readable by the user only, and replaced by the new
token each session returns. Without a token, or on battery unless allowed, nothing is captured and
the colour of the focused window applies. If the portal refuses a stored token and the user cancels
the dialog it opens, the token is forgotten, so the dialog does not come back on the next full
screen. Plasma shows its screen capture indicator for as long as the session is open. A session
opens only after one second of full screen, so a quick toggle does not reach the portal. The daemon
hands the PipeWire descriptor of the session to `gst-launch-1.0`, which asks the compositor for at
most the configured frame rate, scales the image down to a 64 by 36 RGB thumbnail and writes it to a
pipe; the daemon never receives the full image, and keeps no frame. The outer ring of the keyboard,
function row, space row and both side columns, takes the colours of the matching screen edges, and
the four dominant colours of the thumbnail, found by k-means, replace the master hues of the flowing
core.

The keyboard sleep follows what happens on the computer. OpenRGB puts the keyboard to sleep after
the sleep delay without a key press, whatever plays. With the sleep policy, the daemon suspends that
sleep while sound plays, and forces it again as soon as the laptop runs on battery or the keyboard
battery is low. It sets the `LogitechHIDPP20IdleSettings` of the server through the SDK, as a local
client of protocol version 6 granted only to a loopback connection; the server applies them within
half a second. The settings are not saved: a restart of the server starts from its defaults, and the
daemon sets them again on its next change.

The daemon degrades on its own. It follows the `OnBattery` property of UPower on the system bus:
on battery, animations run at the battery frame rate. It reads the keyboard battery from the
`power_supply` entry that the HID++ driver publishes, every refresh interval and on every power
change: at or below the threshold, every colour is capped to the low-battery brightness. The
per-frame packet share follows the frame rate, so the packet ceiling holds at both rates.

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

## How to allow the keyboard to follow full screen windows

1. Ask for the grant; Plasma opens its screen sharing dialog.

   ```bash
   rgb-screen grant
   ```

2. Choose the monitor and allow, ticking the option that keeps the permission. The next full
   screen windows are then captured without a dialog.

3. Withdraw the grant when it is no longer wanted.

   ```bash
   rgb-screen revoke
   ```

## How to run a focus timer on the keyboard

1. Start a timer; the function row fills from F1 to F12 as time passes.

   ```bash
   rgb-focus 25m
   ```

   The duration takes `s`, `m` or `h`, minutes when no unit is given, up to 24 hours.

2. Stop it before the end if needed.

   ```bash
   rgb-focus stop
   ```

## How to check what the lighting daemon records

1. Show the links of the capture stream of the daemon.

   ```bash
   pw-link --links | grep -A2 rgb-effects-monitor
   ```

   Nothing printed means no capture runs. Otherwise the only inputs must be `monitor_FL` and
   `monitor_FR` of the output sink, never a source such as the microphone or
   `Easy Effects Source`.

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
| `environment.sessionVariables.GTK_MODULES` | `colorreload-gtk-module:window-decorations-gtk-module` |
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

### G key commands

| Key | Shortcut | Command |
| --- | --- | --- |
| G1 | `Launch (5)` | Shell aliases, generated from `programs.zsh.shellAliases`, opened in `less` |
| G3 | `Launch (7)` | `~/.config/nixos` opened in Neovim in Konsole |

### Options

| Option | Default | Description |
| --- | --- | --- |
| `custom.plasma.enable` | `false` | Plasma 6, SDDM on Wayland, keyboard layout, fonts, desktop OpenSnitch rules |
| `custom.firefox.enable` | `false` | Firefox with its policies, extensions and OpenSnitch rule |
| `custom.rgbEffects.enable` | `false` | Effects daemon `rgb-effects` in the graphical session |
| `custom.rgbEffects.user` | `"mowsoon"` | Only user whose session starts the daemon |
| `custom.rgbEffects.device` | `"G915 X LS"` | OpenRGB device the effects are painted on |
| `custom.rgbEffects.refreshSeconds` | `60` | Interval of recomputation while nothing animates |
| `custom.rgbEffects.fps` | `20` | Frame rate while keys have been pressed within the sleep delay |
| `custom.rgbEffects.batteryFps` | `10` | Frame rate of animations while the laptop runs on battery |
| `custom.rgbEffects.lowBattery.threshold` | `20` | Keyboard battery percentage at or below which brightness is capped |
| `custom.rgbEffects.lowBattery.brightness` | `0.4` | Brightness ceiling while the keyboard battery is low |
| `custom.rgbEffects.keys.enable` | `false` | Socket-activated key reader `rgb-keyreader` for key-reactive effects |
| `custom.rgbEffects.keys.mode` | `"position"` | `position` forwards the key code, `pulse` only the fact of a key press |
| `custom.rgbEffects.screen.enable` | `false` | Screen capture of full screen windows through the ScreenCast portal |
| `custom.rgbEffects.screen.fps` | `8` | Largest frame rate of the screen thumbnail |
| `custom.rgbEffects.screen.paletteMs` | `500` | Interval of the dominant colour computation |
| `custom.rgbEffects.screen.onBattery` | `false` | Keep capturing while the laptop runs on battery |
| `custom.rgbEffects.notifications.enable` | `false` | Notification waves through the `rgb-notifywatch` bus monitor |
| `custom.rgbEffects.sleepPolicy.enable` | `false` | Keyboard sleep suspended while sound plays, forced on battery |
| `custom.rgbEffects.audio.enable` | `false` | Effects driven by the sound played, from the default sink monitor |
| `custom.rgbEffects.audio.color` | `"#7dff8a"` | Colour of the spectrum and of the waves while sound plays |
| `custom.rgbEffects.audio.spectrumGain` | `0.7` | Weight of the spectrum mask over the background |
| `custom.rgbEffects.audio.hueRange` | `60` | Largest hue rotation, in degrees, driven by the harmony |
| `custom.rgbEffects.audio.silenceSeconds` | `5` | Silence after which the audio gains fade out |
| `custom.rgbEffects.hud.bindings` | Edit, file, navigation, window, desktop and system keys | Combination of `ctrl`, `alt`, `super` to category to key labels |
| `custom.rgbEffects.hud.colors` | One colour per category, `focus` and `clock` | Colour of each HUD category |
| `custom.rgbEffects.hud.dim` | `0.25` | Brightness left to the lower layers while a modifier is held |
| `custom.rgbEffects.hud.clockHoldMs` | `500` | Hold time of Right Ctrl before the binary clock shows |
| `custom.rgbEffects.physics.minimumBrightness` | `0.6` | Brightness ceiling of the key-reactive layer when the schedule is darker |
| `custom.rgbEffects.physics.emberColdMs` | `800` | Cooling time of a pressed key on a cold key |
| `custom.rgbEffects.physics.emberHotMs` | `2500` | Cooling time of a pressed key on the hottest key |
| `custom.rgbEffects.physics.sandWordsPerMinute` | `15` | Typing speed below which presses drop falling grains |
| `custom.rgbEffects.palette.size` | `8` | Number of colours of the quantised frame, from 6 to 8 |
| `custom.rgbEffects.budget.packetsPerSecond` | `180` | Ceiling of HID++ packets per second |
| `custom.rgbEffects.background.idleSeconds` | `30` | Delay without key press before the cellular automaton |
| `custom.rgbEffects.sleepSeconds` | `300` | Delay without key press after which nothing animates |
| `custom.rgbEffects.windowColors` | Six applications | Primary hue per KWin resource class |
| `custom.rgbEffects.schedule` | Five keyframes from night to evening | Hue and brightness ceiling keyframes `{ time; color; brightness; }`, sorted by time |

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
| plasma-manager | <https://github.com/nix-community/plasma-manager> |
| plasma-manager options | <https://nix-community.github.io/plasma-manager/options.html> |
| `services.desktopManager.plasma6` | <https://search.nixos.org/options?channel=unstable&query=services.desktopManager.plasma6> |
| `services.displayManager.sddm` | <https://search.nixos.org/options?channel=unstable&query=services.displayManager.sddm> |
| `fonts.packages` | <https://search.nixos.org/options?channel=unstable&query=fonts.packages> |
| `i18n.extraLocaleSettings` | <https://search.nixos.org/options?channel=unstable&query=i18n.extraLocaleSettings> |
