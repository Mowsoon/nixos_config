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
    custom.network.opensnitch = {
      allowedExecutables = {
        firefox = "${config.programs.firefox.finalPackage}/lib/firefox/firefox";
        kioworker = "${pkgs.kdePackages.kio}/libexec/kf6/.kioworker-wrapped";
        plasmashell = "${pkgs.kdePackages.plasma-workspace}/bin/.plasmashell-wrapped";
      }
      // lib.optionalAttrs config.services.fwupd.enable {
        fwupdmgr = "${config.services.fwupd.package}/bin/.fwupdmgr-wrapped";
      };
      allowedExecutablePatterns.discover = "^/nix/store/[a-z0-9]{32}-discover-[^/]+/(bin|libexec)/\\.(plasma-discover|DiscoverNotifier)-wrapped$";
    };
  };
}
