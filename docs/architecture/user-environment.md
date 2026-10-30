# User environment

## Overview

Everything the user `mowsoon` runs is declared: the shell, the editor, the command-line tools, the
desktop applications and their user services. Home Manager builds this environment from
`home/mowsoon/` and activates it with each system generation. The home directory itself is a
persistent subvolume, so files the user creates survive reboots; the declared configuration files
in it are links into the Nix store, rewritten at each activation.

### Home Manager

Home Manager runs as a NixOS module, configured in `hosts/hephaestus/home.nix`:

- `useGlobalPkgs` makes it use the system `pkgs`, with the same overlays and unfree allowlist;
- `useUserPackages` installs user packages into the user profile of the system generation, so a
  rollback of the system also rolls back the user environment;
- `sharedModules` loads the NixVim Home Manager module.

A file managed by Home Manager is read-only. A change made in an application that tries to write
such a file fails, or is overwritten at the next activation: the change belongs in
`home/mowsoon/`.

### Shell

zsh is the login shell, with completion, autosuggestions, syntax highlighting and the
powerlevel10k prompt. The prompt configuration is the file `home/mowsoon/p10k.zsh`; its instant
prompt block is placed first in `.zshrc` so the prompt appears before the plugins load. Aliases
make `rm`, `cp` and `mv` interactive and give short names to the infrastructure clients.

The zsh history saves 20 000 lines, is shared between open shells, drops consecutive repeats and
skips commands typed with a leading space. It keeps older duplicates, because the `match_prev_cmd`
suggestion strategy relies on the order of the history; searches skip the duplicates instead.
Up and Down search the history for the typed text anywhere in a command. atuin records every
command with its directory, exit code and duration in a SQLite database under
`~/.local/share/atuin`, and owns Ctrl+R: a full-screen search whose filter Ctrl+R cycles between
all history, the host, the session, the directory and the current Git repository. Enter puts the
chosen command on the line without running it. Sync and the update check are off, so atuin opens
no network connection, and its secrets filter keeps recognisable tokens out of the database. Its
settings file is forced: atuin writes a default one the first time it runs, which would otherwise
stop the Home Manager activation.

The line editor uses the emacs keymap, declared because zsh would otherwise pick the vi keymap
from `EDITOR=nvim`. The keys kitty sends for Home, End, Delete and the Ctrl-modified arrows,
Backspace and Delete are bound to their usual editing actions, and `/` is removed from
`WORDCHARS`, so word motions and deletions stop at each component of a path. Autosuggestions
propose the rest of a command from the history, preferring what usually follows the previous
command (`match_prev_cmd`), then from the completion system when the history has no match; Right
accepts the whole suggestion and Ctrl+Right one word of it. atuin prepends its own strategy when
it loads, so the declared strategy list is set again after it.

Plugins come from nixpkgs through `programs.zsh.plugins` or a dedicated Home Manager module, so
the flake lock pins them and no plugin manager runs. An Oh My Zsh plugin that stands alone is
sourced from the `oh-my-zsh` package without loading the framework.

fzf is the fuzzy finder behind interactive selection. Tab opens the completions in fzf through
fzf-tab, which is sourced right after `compinit` and before the plugins that wrap line editor
widgets; `**` followed by Tab still triggers the path completion of fzf itself. Completion matches
case-insensitively and groups its candidates under titles, and zsh-completions adds definitions
for commands that zsh does not cover. Ctrl+T inserts a file path with a bat preview, Alt+C enters
a directory with an eza tree preview; the history widget of fzf is off and Ctrl+R belongs to atuin.
fd lists the candidates,
hidden files included and `.git` excluded. forgit adds interactive Git commands with previews. The
fzf colours are ANSI indices, so they follow the terminal palette.

Variables read only by interactive shells (`MANPAGER`, the `FZF_*` settings) are exported in
`.zshrc`. Home Manager session variables are sourced once per login session and guarded by a
marker inherited by every terminal, so a change to them would wait for the next login.

Syntax highlighting colours the command line as it is typed, including matching brackets, with
the ANSI colours of the terminal. Output gets colour the same way:

- bat shows files with syntax highlighting and Git marks, and renders the manual pages through
  `MANPAGER`; its `base16` theme uses the ANSI colours, so it follows the terminal palette;
- eza lists files with icons and a Git column behind `ll`, `la` and `lt`, while `ls` stays GNU
  `ls`, whose options differ from those of eza (`-t` sorts by time in `ls` and takes a field in
  eza);
- `kubectl`, and so `k`, run kubecolor, which calls `kubectl` and colours its output; the alias is
  declared in `shell.nix` rather than by the kubecolor module, whose alias option reads
  `home.packages` and loops through the G key commands, which list the aliases;
- `grep`, `diff` and `ip` ask for colour when they write to a terminal.

Moving between directories relies on zsh itself where it can:

- `AUTO_CD` enters a directory typed alone, and `AUTO_PUSHD` stacks every directory left, so
  `cd -<Tab>` lists the recent ones;
- named directories (`programs.zsh.dirHashes`) act as declared bookmarks: `cd ~nixos`, completed
  by `~<Tab>`, and shown under that name in the prompt;
- zoxide records each visited directory and jumps to the best match of a word with `z <word>`,
  ranked by frequency and recency; its database lives in `~/.local/share/zoxide`;
- the Oh My Zsh `dirhistory` plugin moves back and forward through the visited directories with
  Alt+Left and Alt+Right, and to the parent with Alt+Up.

Instead of a plugin that returns every new shell to the last directory, kitty opens new windows
and tabs in the directory of the current one, which keeps the directory chosen by the launcher
of a terminal (a G key, "Open terminal here").

The system side of zsh is declared in `home.nix`: `programs.zsh.enable` installs the shell for
login, and `enableGlobalCompInit = false` leaves completion initialisation to the user
configuration, which avoids running it twice.

### Terminal

kitty is the terminal, configured in `home/mowsoon/terminal.nix`, and Plasma uses it as its
default terminal application: "Open terminal here", terminal applications launched from a menu or
a file association, and `Ctrl+Alt+T`. Konsole is removed from the Plasma packages, so the terminal
panel of Dolphin, which embeds Konsole, is gone.

Its palette, named verdigris, is its own: a petrol background with a teal accent, distinct from the
bordeaux of Plasma and the violet of the editor while sharing their yellow and the teal secondary
of Plasma. The background is slightly translucent and blurred by KWin. The font is Maple Mono NF,
whose Nerd Font glyphs draw the prompt icons, at 10.5 points. The update check of kitty is off, so
it opens no outbound connection.

kitty sets `TERM=xterm-kitty`, which most remote servers do not know. The system SSH client sends
`TERM=xterm-256color` instead through `SetEnv`, which servers accept for `TERM` without any
`AcceptEnv` setting. Locally the kitty terminfo entry is installed system-wide, so root shells and
`sudo` keep a working terminal.

### Editor

Neovim is configured with NixVim under `home/mowsoon/editor/`: core options, key mappings and
commands in `cores/`, plugins grouped by role in `plugins/dev`, `plugins/ui` and
`plugins/utils`. Plugins and language servers come from the Nix store; nothing is downloaded at
editor start. Neovim is the default editor through `EDITOR`.
The key mappings are listed in [Editor key mappings](editor-keymaps.md).

### Command-line tools and toolchains

Monitoring, network and file tools, bat and eza, the infrastructure clients (`kubectl`, `helm`, `flux`,
`clusterctl`, `kind`, `terraform`, `azure-cli`, `ansible`), Go and Python are installed globally
for the user. `~/go/bin` is on the `PATH` for tools installed with `go install`.

Other languages and project-specific versions come from the development shell of each project.
direnv with nix-direnv loads that shell when entering the project directory and caches it, so the
shell survives a garbage collection until the project changes.

### Git

Git uses the identity `Mowsoon` and creates repositories on the branch `main`. Commit signing is a
Phase 8 subject of the migration roadmap.

### Desktop applications and user services

Discord, Spotify, LibreOffice and Solaar are user packages. Two user services run in the graphical
session: the OpenSnitch UI, which shows the prompts of the outbound firewall, and EasyEffects, the
audio effects processor. Their own settings are kept in the persistent home.

The EasyEffects input preset `microphone` is declared: `home/mowsoon/audio/microphone.json` holds
it as EasyEffects exports it, Home Manager links it into `~/.local/share/easyeffects/input/`, and
the service loads it at start through the EasyEffects socket. The preset is read-only; a setting
changed in the EasyEffects window is lost at the next start unless it is exported back into the
repository. The chain and its tuning are described in [Hardware](hardware.md).

### Default applications

The association between file types and applications is declared in `home/mowsoon/mime.nix`.
Home Manager writes `~/.config/mimeapps.list` as a read-only link into the store, so the Plasma
"Default Applications" page and the "Remember application association" box of "Open With" no
longer save anything: a new association is a change in Nix. Glob keys such as `image/*` are
expanded at build time against the shared-mime-info database, and an exact key wins over a glob,
which is how `text/html` goes to Firefox while the rest of `text/*` goes to Neovim. Neovim is a
terminal application; Plasma opens it in kitty.

### Docker

Docker runs as a rootful daemon, started on the first use of its socket rather than at boot. Its
storage is the `@docker` subvolume, excluded from snapshots, and a weekly prune removes every unused
image, container and network. The NVIDIA container toolkit generates a Container Device Interface
(CDI) specification, so containers request the GPU by name. The user is not in the `docker` group:
Docker commands run through `sudo`. The OpenSnitch rule matches `dockerd` and `docker-proxy` of any
moby version.

### Claude desktop application

The Claude desktop application has no nixpkgs package. `pkgs/claude-desktop/package.nix`
repackages the official Debian archive:

- `autoPatchelfHook` rewrites the interpreter and library paths of the Electron binary to point at
  the Nix store;
- a wrapper adds the tools the Cowork virtual machine needs to `PATH` (`qemu`, `virtiofsd`,
  `socat`, `bubblewrap`) and enables the native Wayland backend when `NIXOS_OZONE_WL` is set;
- `chrome-sandbox` stays an ordinary executable: the Electron sandbox relies on unprivileged user
  namespaces instead of a setuid helper.

The application expects OVMF firmware files and `virtiofsd` at Debian paths under `/usr`.
`modules/desktop/claude-desktop.nix` creates these paths as symbolic links into the Nix store with
systemd-tmpfiles at every boot, since the root is rebuilt each time.

The application downloads Claude Code at runtime into `~/.config/Claude/claude-code/`. That binary
is built for a generic Linux distribution and runs through `nix-ld`, which provides a dynamic
loader at the standard path. Its OpenSnitch rule is a pattern that tolerates the version
directories.

## How to add a command-line tool

1. Add the package to `home.packages` in `home/mowsoon/packages.nix`.
2. If the tool opens network connections, add its OpenSnitch rule to
   `hosts/hephaestus/opensnitch.nix`, as described in [Network](network.md).
3. If the package is unfree, add its name to `custom.unfreePackages` in `hosts/hephaestus/home.nix`.
4. Apply the configuration.

## How to import the zsh history into atuin

atuin records only the commands run after it is installed. The existing zsh history is copied
into its database once; `~/.zsh_history` is read, not changed.

1. Import the history.

   ```bash
   atuin import zsh
   ```

2. Check the count of commands in the database.

   ```bash
   atuin stats
   ```

## How to use a project development shell

1. Declare the shell in the flake of the project, as `devShells.x86_64-linux.default`.
2. In the project directory, ask direnv to load it.

   ```bash
   echo 'use flake' > .envrc
   direnv allow
   ```

   `direnv allow` approves the content of `.envrc`; direnv refuses an unknown or modified file.

3. Leave and enter the directory again: the tools of the shell appear and disappear with it.

## How to run a container with the GPU

1. Request every NVIDIA device through CDI.

   ```bash
   sudo docker run --rm --device nvidia.com/gpu=all ubuntu nvidia-smi
   ```

## How to update the Claude desktop application

1. Set `version` in `pkgs/claude-desktop/package.nix` to the new release.
2. Download the new archive into the store and print its hash.

   ```bash
   nix-prefetch-url https://downloads.claude.ai/claude-desktop/apt/stable/pool/main/c/claude-desktop/claude-desktop_<version>_amd64.deb
   ```

   `<version>` is the new release, such as `2.26454.2`.

3. Copy the printed hash into `sha256`, then apply the configuration.

## Reference

### Files under `home/mowsoon/`

| File | Content |
| --- | --- |
| `default.nix` | Imports and `home.stateVersion` |
| `shell.nix` | zsh, history, atuin, aliases, keymap, completion, navigation, fzf, plugins, powerlevel10k |
| `p10k.zsh` | Prompt configuration generated by `p10k configure` |
| `terminal.nix` | kitty, its palette and font, default terminal of Plasma |
| `git.nix` | Git identity and defaults |
| `packages.nix` | Command-line tools, toolchains, direnv, bat, eza, kubecolor |
| `audio.nix` | EasyEffects service and its declared input preset |
| `audio/microphone.json` | EasyEffects input preset for the built-in microphone |
| `desktop.nix` | Desktop applications, OpenSnitch UI |
| `mime.nix` | Default applications, zathura, mpv |
| `shortcuts.nix` | Plasma global shortcuts: KRunner and the G keys of the G915 X |
| `editor/nixvim.nix` | NixVim entry point |
| `editor/cores/` | Options, key mappings, commands, colour scheme |
| `editor/plugins/` | Plugins grouped in `dev`, `ui` and `utils` |

### Shell aliases

| Alias | Command |
| --- | --- |
| `rm` | `rm -I --preserve-root` |
| `cp` | `cp -i` |
| `mv` | `mv -i` |
| `ll`, `la` | `eza -l`, `eza -la`, with icons and the Git column |
| `lt` | `eza --tree --level=2` |
| `diff`, `ip` | With colour (`--color=auto`, `-color=auto`) |
| `kubectl` | `kubecolor` |
| `k` | `kubectl` |
| `f` | `flux` |
| `cctl` | `clusterctl` |
| `tf` | `terraform` |
| `sudo` | `sudo` followed by a space, so aliases expand after `sudo` |
| `nrt`, `nrs`, `nrb` | `nixos-rebuild test`, `switch`, `boot` on `#hephaestus` with `--elevate sudo` |
| `nrbr` | `nrb`, then `systemctl reboot` when it succeeds |
| `nrr` | `sudo nixos-rebuild switch --rollback` |
| `nkern` | Booted and current kernel paths; a difference means a reboot is pending |
| `cdn` | `cd ~/.config/nixos` |
| `hib`, `sus`, `sush` | `systemctl hibernate`, `suspend`, `suspend-then-hibernate` |
| `jb`, `jbu <unit>` | `journalctl -b`, `journalctl -b --no-pager -u <unit>` |
| `jke` | `journalctl -k -p err`, kernel messages of priority error and above |
| `gst`, `gaa`, `gcm` | `git status`, `git add -A`, `git commit -m` |
| `ns <pkg>...` | Shell function: `nix shell nixpkgs#<pkg>...` |
| `ga`, `gd`, `glo`, `gcb` | forgit: interactive `git add`, `diff`, `log`, branch checkout; `gi` downloads `.gitignore` templates |

### Line editor keys

| Key | Action |
| --- | --- |
| Home, End | `beginning-of-line`, `end-of-line` |
| Delete | `delete-char` |
| Ctrl+Left, Ctrl+Right | `backward-word`, `forward-word`; Ctrl+Right also accepts one word of a suggestion |
| Ctrl+Backspace, Ctrl+Delete | `backward-kill-word`, `kill-word` |
| Shift+Tab | `reverse-menu-complete` |
| Right | Accepts the whole suggestion |
| Tab | Completion in fzf; `<` and `>` switch between groups |
| `**` then Tab | fzf path completion |
| Ctrl+T | Insert a file path, with preview |
| Alt+C | Enter a directory, with preview |
| Ctrl+R | atuin history search; Ctrl+R again cycles the filter |
| Up, Down | Previous, next history entry containing the typed text |

### Shell navigation

| Feature | Use |
| --- | --- |
| `AUTO_CD` | `<dir>` alone enters it |
| `AUTO_PUSHD`, `PUSHD_IGNORE_DUPS`, `PUSHD_SILENT` | `cd -<Tab>` lists recent directories, `cd -<n>` returns to one |
| Named directories | `~nixos` is `~/.config/nixos`, `~private` is `~/.config/nixos-private` |
| zoxide | `z <word>...` jumps to the best ranked match, `zi <word>...` picks one in fzf |
| `dirhistory` | Alt+Left, Alt+Right: previous, next directory; Alt+Up: parent |

### Terminal settings

| Setting | Value |
| --- | --- |
| Font | Maple Mono NF (`maple-mono.NF`), 10.5 points, ligatures off under the cursor |
| Background | `#0e1719`, opacity 0.92, blurred |
| Foreground, accent | `#d5e2df`, `#5fb3a8` |
| Scrollback | 10 000 lines |
| New window, new tab | `Ctrl+Shift+Enter`, `Ctrl+Shift+T`, both in the current directory |
| Update check | Off |
| Plasma default terminal | `TerminalApplication=kitty`, `TerminalService=kitty.desktop` in `kdeglobals` |
| Launch shortcut | `Ctrl+Alt+T` |
| SSH | `SetEnv TERM=xterm-256color` in `/etc/ssh/ssh_config` |
| Local terminfo | `kitty.terminfo` in the system packages |

### Docker settings

| Setting | Value |
| --- | --- |
| `virtualisation.docker.enableOnBoot` | `false`, socket activation |
| `virtualisation.docker.autoPrune` | Weekly, `--all` |
| `hardware.nvidia-container-toolkit.enable` | Follows `custom.nvidia.enable` |
| Storage | `/var/lib/docker` on the `@docker` subvolume |

### Claude desktop paths

| Path | Content |
| --- | --- |
| `/usr/share/OVMF/OVMF_CODE_4M.fd` | Link to the OVMF code firmware |
| `/usr/share/OVMF/OVMF_VARS_4M.fd` | Link to the OVMF variable template |
| `/usr/bin/virtiofsd` | Link to `virtiofsd` |
| `~/.config/Claude/claude-code/<version>/<hash>/claude` | Claude Code binary, run through `nix-ld` |

### Default applications

| Types | Application |
| --- | --- |
| `text/html`, `application/xhtml+xml`, `http`, `https`, `about` and unknown URL schemes | Firefox |
| `text/*` except HTML, JSON, XML, YAML, TOML, shell scripts | Neovim |
| `application/pdf` | zathura with the MuPDF plugin |
| `image/*` | Gwenview |
| `video/*`, `audio/*` | mpv |
| `inode/directory` | Dolphin |
| Zip, tar, compressed tar, gzip, 7z, RAR | Ark |

### Options

| Option | Default | Description |
| --- | --- | --- |
| `custom.docker.enable` | `false` | Docker daemon, socket activation, weekly prune, NVIDIA CDI |
| `custom.claudeDesktop.enable` | `false` | Claude desktop application, Cowork paths, `nix-ld` |

### Upstream documentation

| Subject | Link |
| --- | --- |
| Home Manager manual | <https://nix-community.github.io/home-manager/> |
| Home Manager options | <https://nix-community.github.io/home-manager/options.xhtml> |
| NixVim options | <https://nix-community.github.io/nixvim/> |
| nix-direnv | <https://github.com/nix-community/nix-direnv> |
| NVIDIA CDI | <https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/cdi-support.html> |
| nix-ld | <https://github.com/nix-community/nix-ld> |
| `virtualisation.docker` | <https://search.nixos.org/options?channel=unstable&query=virtualisation.docker> |
| `programs.nix-ld` | <https://search.nixos.org/options?channel=unstable&query=programs.nix-ld> |
| `services.easyeffects` | <https://nix-community.github.io/home-manager/options.xhtml#opt-services.easyeffects.enable> |
| kitty configuration | <https://sw.kovidgoyal.net/kitty/conf/> |
| zoxide | <https://github.com/ajeetdsouza/zoxide> |
| zsh-autosuggestions | <https://github.com/zsh-users/zsh-autosuggestions> |
| bat | <https://github.com/sharkdp/bat> |
| fzf | <https://junegunn.github.io/fzf/> |
| atuin | <https://docs.atuin.sh/> |
| zsh-history-substring-search | <https://github.com/zsh-users/zsh-history-substring-search> |
| fzf-tab | <https://github.com/Aloxaf/fzf-tab> |
| forgit | <https://github.com/wfxr/forgit> |
| eza | <https://github.com/eza-community/eza> |
| kubecolor | <https://kubecolor.github.io/> |
| zsh line editor | <https://zsh.sourceforge.io/Doc/Release/Zsh-Line-Editor.html> |
| `programs.zsh.dirHashes` | <https://nix-community.github.io/home-manager/options.xhtml#opt-programs.zsh.dirHashes> |
| `programs.kitty` | <https://nix-community.github.io/home-manager/options.xhtml#opt-programs.kitty.enable> |
| `xdg.mimeApps` | <https://nix-community.github.io/home-manager/options.xhtml#opt-xdg.mimeApps.enable> |
| MIME applications specification | <https://specifications.freedesktop.org/mime-apps-spec/latest/> |
