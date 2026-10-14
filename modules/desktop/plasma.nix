{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.custom.plasma;
in
{
  options.custom.plasma = {
    enable = lib.mkEnableOption "the Plasma 6 desktop on Wayland with SDDM";
  };

  config = lib.mkIf cfg.enable {
    services = {
      desktopManager.plasma6.enable = true;
      displayManager.sddm = {
        enable = true;
        wayland.enable = true;
      };
      xserver.xkb.layout = "fr";
    };

    environment.sessionVariables.NIXOS_OZONE_WL = "1";

    fonts.packages = with pkgs; [
      nerd-fonts.jetbrains-mono
      noto-fonts
      noto-fonts-color-emoji
    ];

    programs.firefox.enable = true;
  };
}
