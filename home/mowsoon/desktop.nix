{ pkgs, ... }:
{
  home.packages = with pkgs; [
    discord
    spotify
    libreoffice-qt
    solaar
  ];

  programs.obsidian.enable = true;

  services.opensnitch-ui.enable = true;
}
