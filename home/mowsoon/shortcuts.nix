{
  config,
  lib,
  pkgs,
  ...
}:
let
  kitty = lib.getExe config.programs.kitty.package;
  nvim = lib.getExe' config.programs.nixvim.build.package "nvim";
  less = lib.getExe pkgs.less;
  repository = "${config.xdg.configHome}/nixos";
  rgbFocus = lib.getExe' (pkgs.callPackage ../../pkgs/rgb-effects/package.nix { }) "rgb-focus";
  systemStatus = pkgs.writeShellApplication {
    name = "system-status";
    runtimeInputs = [
      pkgs.coreutils
      pkgs.libnotify
    ];
    text = ''
      differs() {
        [ "$(readlink "/run/booted-system/$1")" != "$(readlink "/run/current-system/$1")" ]
      }

      free=$(df --output=avail --block-size=G /nix | tail -n 1 | tr -d ' ')
      used=$(df --output=pcent /nix | tail -n 1 | tr -d ' ')

      if differs kernel || differs initrd || differs kernel-modules; then
        reboot="Reboot pending: kernel, initrd or modules changed"
        urgency=critical
      else
        reboot="No reboot pending"
        urgency=normal
      fi

      body=$(printf '%s free on /nix (%s used)\n%s' "$free" "$used" "$reboot")
      notify-send --app-name="System status" --icon=computer --urgency="$urgency" "System status" "$body"
    '';
  };
  aliases = config.programs.zsh.shellAliases;
  width = lib.foldl' (widest: name: lib.max widest (lib.stringLength name)) 0 (lib.attrNames aliases);
  pad = name: name + lib.strings.replicate (width - lib.stringLength name) " ";
  aliasSheet = pkgs.writeText "zsh-aliases" (
    lib.concatStringsSep "\n" (lib.mapAttrsToList (name: command: "${pad name}  ${command}") aliases)
    + "\n"
  );
in
{
  programs.plasma = {
    enable = true;
    shortcuts = {
      "services/org.kde.krunner.desktop"._launch = [
        "Alt+Space"
        "Alt+F2"
        "Search"
        "Meta+Space"
      ];
      "services/kitty.desktop"._launch = "Ctrl+Alt+T";
    };
    hotkeys.commands = {
      show-aliases = {
        name = "Show the shell aliases";
        key = "Launch (5)";
        command = "${kitty} ${less} ${aliasSheet}";
      };
      show-editor-keymaps = {
        name = "Show the editor key mappings";
        key = "Launch (6)";
        command = "${kitty} ${nvim} -R ${repository}/docs/architecture/editor-keymaps.md";
      };
      open-nixos-config = {
        name = "Open the NixOS configuration";
        key = "Launch (7)";
        command = "${kitty} --directory ${repository} ${nvim} .";
      };
      start-focus = {
        name = "Start a focus timer on the keyboard";
        key = "Launch (8)";
        command = "${rgbFocus} 25m";
      };
      show-system-status = {
        name = "Show the system status";
        key = "Launch (9)";
        command = lib.getExe systemStatus;
      };
      stop-focus = {
        name = "Stop the focus timer on the keyboard";
        key = "Alt+Launch (8)";
        command = "${rgbFocus} stop";
      };
    };
  };
}
