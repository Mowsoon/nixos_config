{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.custom.plasma;
  kwin = pkgs.kdePackages.kwin.overrideAttrs (old: {
    patches = old.patches ++ [
      ../../pkgs/kwin/0001-workspace-don-t-log-a-critical-error-while-the-sessi.patch
      ../../pkgs/kwin/0002-backends-drm-don-t-warn-about-commits-rejected-after.patch
    ];
  });
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

    system.replaceDependencies.replacements = [
      {
        oldDependency = pkgs.kdePackages.kwin;
        newDependency = kwin;
      }
    ];

    environment = {
      sessionVariables.NIXOS_OZONE_WL = "1";
      etc."xdg/ksmserverrc".text = ''
        [General]
        loginMode[$i]=emptySession
      '';
    };

    fonts.packages = with pkgs; [
      nerd-fonts.jetbrains-mono
      noto-fonts
      noto-fonts-color-emoji
    ];

    custom.network.opensnitch = {
      allowedExecutables = {
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
