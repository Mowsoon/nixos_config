{
  config,
  lib,
  pkgs,
  ...
}:
let
  konsole = lib.getExe' pkgs.kdePackages.konsole "konsole";
  nvim = lib.getExe' config.programs.nixvim.build.package "nvim";
  less = lib.getExe pkgs.less;
  repository = "${config.xdg.configHome}/nixos";
  rgbFocus = lib.getExe' (pkgs.callPackage ../../pkgs/rgb-effects/package.nix { }) "rgb-focus";
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
    shortcuts."services/org.kde.krunner.desktop"._launch = [
      "Alt+Space"
      "Alt+F2"
      "Search"
      "Meta+Space"
    ];
    hotkeys.commands = {
      show-aliases = {
        name = "Show the shell aliases";
        key = "Launch (5)";
        command = "${konsole} -e ${less} ${aliasSheet}";
      };
      show-editor-keymaps = {
        name = "Show the editor key mappings";
        key = "Launch (6)";
        command = "${konsole} -e ${nvim} -R ${repository}/docs/architecture/editor-keymaps.md";
      };
      open-nixos-config = {
        name = "Open the NixOS configuration";
        key = "Launch (7)";
        command = "${konsole} --workdir ${repository} -e ${nvim} .";
      };
      start-focus = {
        name = "Start a focus timer on the keyboard";
        key = "Launch (8)";
        command = "${rgbFocus} 25m";
      };
      stop-focus = {
        name = "Stop the focus timer on the keyboard";
        key = "Alt+Launch (8)";
        command = "${rgbFocus} stop";
      };
    };
  };
}
