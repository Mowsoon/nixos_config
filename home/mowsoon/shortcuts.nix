{
  config,
  lib,
  pkgs,
  ...
}:
let
  konsole = lib.getExe' pkgs.kdePackages.konsole "konsole";
  nvim = lib.getExe' config.programs.nixvim.build.package "nvim";
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
    hotkeys.commands.open-nixos-config = {
      name = "Open the NixOS configuration";
      key = "Launch (7)";
      command = "${konsole} --workdir ${config.xdg.configHome}/nixos -e ${nvim} .";
    };
  };
}
