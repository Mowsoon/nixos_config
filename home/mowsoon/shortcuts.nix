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
      open-nixos-config = {
        name = "Open the NixOS configuration";
        key = "Launch (7)";
        command = "${konsole} --workdir ${config.xdg.configHome}/nixos -e ${nvim} .";
      };
    };
  };
}
