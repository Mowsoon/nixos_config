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

    systemd = {
      services = {
        "drkonqi-coredump-processor@".enable = false;
        restart-lock-screen-after-hibernation = {
          description = "Replace the lock screen that went through hibernation";
          after = [
            "systemd-hibernate.service"
            "systemd-suspend-then-hibernate.service"
          ];
          wantedBy = [
            "systemd-hibernate.service"
            "systemd-suspend-then-hibernate.service"
          ];
          serviceConfig = {
            Type = "oneshot";
            ExecStart = "-${pkgs.procps}/bin/pkill -f kscreenlocker_greet";
          };
        };
      };
      user = {
        services = {
          drkonqi-coredump-pickup.enable = false;
          "drkonqi-coredump-launcher@".enable = false;
          drkonqi-sentry-postman.enable = false;
        };
        sockets.drkonqi-coredump-launcher.enable = false;
        timers.drkonqi-sentry-postman.enable = false;
        paths.drkonqi-sentry-postman.enable = false;
      };
    };

    system.replaceDependencies.replacements = [
      {
        oldDependency = pkgs.kdePackages.kwin;
        newDependency = kwin;
      }
    ];

    environment = {
      plasma6.excludePackages = [ pkgs.kdePackages.konsole ];
      sessionVariables.NIXOS_OZONE_WL = "1";
      etc."xdg/ksmserverrc".text = ''
        [General]
        loginMode[$i]=emptySession
      '';
    };

    custom.network.opensnitch = {
      allowedExecutables = {
        kioworker = "${pkgs.kdePackages.kio}/libexec/kf6/.kioworker-wrapped";
        krunner = "${pkgs.kdePackages.plasma-workspace}/bin/.krunner-wrapped";
        plasmashell = "${pkgs.kdePackages.plasma-workspace}/bin/.plasmashell-wrapped";
      }
      // lib.optionalAttrs config.services.fwupd.enable {
        fwupdmgr = "${config.services.fwupd.package}/bin/.fwupdmgr-wrapped";
      };
      allowedExecutablePatterns.discover = "^/nix/store/[a-z0-9]{32}-discover-[^/]+/(bin|libexec)/\\.(plasma-discover|DiscoverNotifier)-wrapped$";
    };
  };
}
