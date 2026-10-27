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

After every resume from hibernation, a service kills the lock screen greeter, which the screen
locker restarts at once: the greeter carried through hibernation makes the next sleep hang
([incident](../incidents/sleep-after-hibernation-deadlock.md)).

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

### Theme

`modules/desktop/theme.nix` declares the palette and the fonts through Stylix, imported as a
NixOS module that also loads its Home Manager module. Stylix themes nothing on its own
(`autoEnable` is off): only the KDE and GTK targets are enabled, so the terminal, the editor, the
console and the boot screens keep their own colours.

The palette is a dark base16 scheme named Bordeaux, written in Nix. `base00` to `base07` run from
the darkest background to the lightest text, `base0D` is the accent and the selection, the other
slots carry the semantic colours (errors, warnings, success, links).

- KDE target: a colour scheme `Bordeaux`, and a configuration directory that Home Manager prepends
  to `XDG_CONFIG_DIRS`, where the fonts, the cursor and the module switches are marked immutable.
  The target also ships a look-and-feel package `stylix`, which it would apply with
  `plasma-apply-lookandfeel` at every login and every Home Manager activation. The theme module
  removes both triggers: applying a look-and-feel writes its own values to `~/.config/kdedefaults`
  and deletes from the user files the decoration, the Plasma style and the splash screen that
  plasma-manager writes there, and marking those keys immutable in the user file does not stop
  it. plasma-manager applies the `Bordeaux` scheme instead.
- GTK target: the `adw-gtk3` theme for GTK 3 and GTK 4, recoloured by a generated `gtk.css`, and
  the GTK font. Home Manager owns `settings.ini` and `gtk.css` of both versions.
- The KDE target turns off the `gtkconfig` module of kded, which used to copy the Plasma
  appearance into the GTK files. Without it, nothing rewrites the GTK colour files during a
  session and no `gtk-modules` setting loads the two Plasma GTK modules, so the crash of Electron
  applications on a colour change can no longer happen and `GTK_MODULES` is not set any more
  ([incident](../incidents/electron-gtk-module-unload.md)).
- The accent no longer follows the wallpaper: it is `base0D` of the palette. Plasma writes no
  `AccentColor` to the user `kdeglobals`, so the keyboard lighting effects use their own secondary
  hue in place of the accent.

#### Panel and wallpaper

One panel stands on the left edge, floating, with the launcher, the virtual desktop pager, the
task manager, a separator, the system tray, the clock and the show-desktop button, in that order
from the top. plasma-manager declares it through a desktop script that removes every panel and
creates the declared one, run at the first login after the declaration changes; a panel changed
in the Plasma settings comes back as declared at that point. The desktop scripts need
`plasmashell`, which starts as its own user service, so a first startup script waits for it
([incident](../incidents/plasma-manager-desktop-scripts-before-plasmashell.md)).

The wallpaper is a personal image, so it lives in the private input under `wallpapers/`. The theme
module copies it into a store path of its own, so the system closure holds the image and not the
whole private input, and plasma-manager sets it on every desktop and on the lock screen. The
picture of the account comes from `avatars/` of the private input the same way and is linked as
`~/.face.icon`, which Plasma reads for the launcher and the lock screen while AccountsService has
no icon for the user; `/var/lib/AccountsService` is not persisted, so it never has one.

#### Plasma themes

The Plasma style, the window decoration, the icons, the cursor and the splash screen are
third-party themes first installed with "Get New...". Their original files live in the private
input under `themes/`, so their choice and their source stay out of this public repository. The
theme module builds each of them into the store with `pkgs/theme-recolor`, a Python tool of this
repository that rewrites their fixed colours towards the roles of the palette; the drawing is
never changed.

- Every colour keeps its OKLab lightness. A grey takes the tint of the `base00` to `base07` ramp at
  that lightness; a colour takes the hue of the role of its family (red, orange, yellow, green,
  cyan, blue, purple and pink, brown) and a chroma scaled from the most frequent colour of that
  family, so the shades of one family keep their spread. Colours darker than `base00`, such as the
  black shadows, are kept.
- The tool rewrites the colour attributes and style properties of SVG and SVGZ files, the pixels
  of PNG, JPEG and Xcursor images, the quoted colours of QML files and the colour triples of `rc`
  files. It leaves to Plasma the elements that carry a `ColorScheme-*` class, the `<style>`
  blocks that define those classes, and the invisible `hint` elements.
- Per theme, a family can be sent to another role. The Plasma style sends cyan, its accent, to
  `base0D` and loses its own `colors` file, so its classed elements follow the Bordeaux scheme.
  The cursor and the splash screen send every family to `base0D`: they hold one painted hue, and a
  photograph would break where its hues cross a family boundary.
- None of the five themes followed the colour scheme on its own: the Plasma style imposed its own
  colours through its `colors` file, and the others hold fixed colours only.

Each setting has one owner. Stylix owns the colours, the fonts and the cursor (`stylix.cursor`,
applied through `home.pointerCursor`): it generates the colour scheme, and plasma-manager only
names it. plasma-manager owns the Plasma style, the decoration, the icons and the splash screen;
the panel, the effects and the lock screen will follow it. GTK takes the same icon theme from the
plasma-manager option. The icon theme inherits from `breeze-dark` instead of `gnome`, which is not
installed, so an icon it lacks falls back to a Breeze icon drawn in the colours of the scheme.

At every login Plasma notices that the look-and-feel package named in `kdeglobals` differs from
the one recorded in `~/.config/kdedefaults/package` and writes the defaults of `stylix` there
again. It does so in defaults mode, which leaves the user files alone, and the user files come
first, so the values written by plasma-manager stay in effect.

The recoloured themes reach Plasma through the Home Manager profile, in `XDG_DATA_DIRS`. A copy
installed with "Get New..." under `~/.local/share` or `~/.icons` comes first in the search path
and hides the store version, so it must not come back. KWin resolves the files of a decoration
once, when it loads it: after such a copy is deleted, the running session keeps the deleted paths
and draws the title bar without buttons until the next login.

### Declared and mutable settings

The boundary between what is declared and what is left to Plasma follows one rule: the system
layer is declared, the appearance and the interactive behaviour of the desktop are not, until the
theme is declared. Theming is declared in two parts: the settings of each application first, then
the display: palette and fonts, then the Plasma themes, the panel and the wallpaper.

| Area | Where it lives |
| --- | --- |
| Display manager, session type, session restore, keyboard layout | `modules/desktop/plasma.nix` |
| Palette, fonts and their rendering, GTK theme, cursor | `modules/desktop/theme.nix`, through Stylix |
| Plasma style, decoration, icons, splash screen | `modules/desktop/theme.nix`, through plasma-manager, recoloured from `themes/` of the private input |
| Panel, wallpaper of the desktop and of the lock screen | `modules/desktop/theme.nix`, through plasma-manager, image from `wallpapers/` of the private input |
| Account picture | `modules/desktop/theme.nix`, through Home Manager, image from `avatars/` of the private input |
| Applications installed | `home/mowsoon/desktop.nix`, Firefox in `firefox.nix` |
| Firefox settings, extensions, search engine | `modules/desktop/firefox.nix` |
| Default applications per file type | `home/mowsoon/mime.nix` |
| Outbound rules of desktop components | `plasma.nix` and `hosts/hephaestus/opensnitch.nix` |
| KRunner shortcuts, commands of the G keys | `home/mowsoon/shortcuts.nix`, through plasma-manager |
| Other shortcuts, scaling, desktop icons | Plasma settings, `~/.config` |
| Lid switch, power key, sleep mode | Plasma energy settings (PowerDevil), `~/.config/powerdevilrc` |
| Region and format overrides for the session | Plasma region settings, `~/.config/plasma-localerc` |
| Settings of the applications not yet declared | Each application, under `~/.config` or `~/.local/share` |

The home directory is persistent and snapshotted, so these settings survive reboots and can be
restored from a snapshot. The palette and the fonts are declared, as described in [Theme](#theme);
the terminal, the editor and the boot menu keep their own colours.

### Global shortcuts

plasma-manager writes the declared shortcuts into `~/.config/kglobalshortcutsrc` and leaves every
other entry of the file untouched (`overrideConfig` stays off), so the shortcuts set in the Plasma
settings coexist with the declared ones. A declared entry overwrites a change made to it in the
settings at the next activation. KRunner keeps its default shortcuts and gains Meta+Space.

Each G key of the G915 X reaches Plasma as a dedicated key symbol, set in
[Hardware](hardware.md). A command is bound to that symbol through
`programs.plasma.hotkeys.commands`, which generates one hidden desktop entry whose actions are the
commands; kglobalaccel starts the action, and its output goes to the journal. A new or changed
binding is read by kglobalaccel at the next login. G6 to G9 and the Alt layer apart from Alt+G4
stay unbound on purpose: applications are launched through KRunner, and a key is bound only once
a recurring need appears.

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

The fonts are Stylix roles, installed by the theme module. JetBrains Mono from the Nerd Fonts set
is the monospace role, which covers the terminal and the editor, including the glyphs of the
prompt. Noto Sans and Noto Serif cover text in most scripts, and Noto Color Emoji covers emoji.
Plasma reads the fonts from the immutable `kdeglobals` of Stylix, so the font settings page can no
longer change them. The rendering (antialiasing, slight hinting, vertical BGR subpixel order) is
declared through the fontconfig options of Home Manager, since the font settings page of Plasma
writes it into a file that Home Manager owns.

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

### Theme

| Setting | Value |
| --- | --- |
| `stylix.autoEnable` | `false` |
| Stylix targets | `kde` and `gtk` (NixOS and Home Manager), Flatpak support off |
| `stylix.polarity` | `dark` |
| GTK theme | `adw-gtk3` with the generated `gtk.css` |
| Look-and-feel package | `stylix`, named immutable in `kdeglobals`, never applied |
| Colour scheme | `Bordeaux`, applied by plasma-manager |
| Panel | Left edge, floating, height 46 |
| Panel widgets, top to bottom | `kickoff`, `pager`, `icontasks`, `marginsseparator`, `systemtray`, `digitalclock`, `showdesktop` |
| Wallpaper | `wallpapers/desktop.png` of the private input, desktop and lock screen |
| Account picture | `avatars/mowsoon.png` of the private input, linked as `~/.face.icon` |
| kded `gtkconfig` module | Not loaded, immutable in `kded5rc` |

| Theme | Kind | Private source | Name | Role overrides |
| --- | --- | --- | --- | --- |
| Maia Transparent | Plasma style | `themes/desktoptheme/Maia_Transparent` | `Maia_Transparent` | cyan to `base0D`, `colors` removed |
| Aquarelle | Aurorae decoration | `themes/aurorae/AquarelleRed` | `__aurorae__svg__AquarelleRed` | None |
| material-black-mango-numix | Icons, also for GTK | `themes/icons/Material-Black-Mango-Numix` | `Material-Black-Mango-Numix` | None, inherits `breeze-dark` |
| rage-gothic-light | Cursor, size 24 | `themes/cursors/Rage-Gothic-Light` | `Rage-Gothic-Light` | Every family to `base0D` |
| Jolly-Splash-6 | Splash screen | `themes/look-and-feel/Jolly-Splash-6` | `Jolly-Splash-6` | Every family to `base0D` |

| Colour family | Default role |
| --- | --- |
| Red | `base08` |
| Orange | `base09` |
| Yellow | `base0A` |
| Green | `base0B` |
| Cyan | `base0C` |
| Blue | `base0D` |
| Purple, pink | `base0E` |
| Brown | `base0F` |

| Slot | Colour | Role |
| --- | --- | --- |
| `base00` | `#1a0e11` | Default background |
| `base01` | `#26151a` | Lighter background: alternate rows, headers |
| `base02` | `#3a1f27` | Selection background in text views |
| `base03` | `#6b4a52` | Comments, inactive window blend |
| `base04` | `#a48a90` | Dark foreground |
| `base05` | `#e3d3d6` | Default foreground |
| `base06` | `#f0e4e6` | Light foreground |
| `base07` | `#faf3f4` | Lightest foreground |
| `base08` | `#e06c75` | Errors, negative text |
| `base09` | `#d9895b` | Constants |
| `base0A` | `#d8b46a` | Active window blend |
| `base0B` | `#9cba7f` | Success, positive text |
| `base0C` | `#7fb3ad` | Support, escape sequences |
| `base0D` | `#c04a63` | Accent, selection, focus |
| `base0E` | `#b07fc0` | Keywords, GTK warnings |
| `base0F` | `#8c4a3a` | Deprecated, embedded |

### Fonts

| Role | Package | Family | Size |
| --- | --- | --- | --- |
| Sans serif | `noto-fonts` | Noto Sans | 10 for applications, desktop and popups |
| Serif | `noto-fonts` | Noto Serif | 10 |
| Monospace | `nerd-fonts.jetbrains-mono` | JetBrainsMono Nerd Font | 11 |
| Emoji | `noto-fonts-color-emoji` | Noto Color Emoji | Not applicable |

| Rendering | Value |
| --- | --- |
| `fonts.fontconfig.antialiasing` | `true` |
| `fonts.fontconfig.hinting` | `slight` |
| `fonts.fontconfig.subpixelRendering` | `vertical-bgr` |

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
| G2 | `Launch (6)` | Working copy of `docs/architecture/editor-keymaps.md`, read-only in Neovim |
| G3 | `Launch (7)` | `~/.config/nixos` opened in Neovim in Konsole |
| G4 | `Launch (8)` | `rgb-focus 25m`: 25-minute focus timer on the function row |
| Alt+G4 | `Alt+Launch (8)` | `rgb-focus stop` |
| G5 | `Launch (9)` | Notification: free space on `/nix`, reboot pending when the kernel, initrd or modules differ from the booted ones |

### Options

| Option | Default | Description |
| --- | --- | --- |
| `custom.plasma.enable` | `false` | Plasma 6, SDDM on Wayland, keyboard layout, desktop OpenSnitch rules |
| `custom.theme.enable` | `false` | Stylix palette and fonts for the KDE and GTK targets, font rendering |
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
| Stylix | <https://github.com/nix-community/stylix> |
| Stylix options | <https://nix-community.github.io/stylix/options/platforms/nixos.html> |
| OKLab colour space | <https://bottosson.github.io/posts/oklab/> |
| Plasma theme colours | <https://develop.kde.org/docs/plasma/theme/theme-colors/> |
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
