{ pkgs, ... }:
{
  home.packages = with pkgs; [
    discord
    spotify
    libreoffice-qt
    solaar
  ];

  services.opensnitch-ui.enable = true;
}
