{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.custom.nvidia;
  driver = config.hardware.nvidia.package.out;
in
{
  options.custom.nvidia = {
    enable = lib.mkEnableOption "the NVIDIA driver with open kernel modules on the discrete GPU";
  };

  config = lib.mkIf cfg.enable {
    custom.unfreePackages = [
      "nvidia-x11"
      "nvidia-settings"
    ];

    services.xserver.videoDrivers = [ "nvidia" ];

    hardware = {
      graphics = {
        enable = true;
        enable32Bit = true;
        extraPackages = [ pkgs.nvidia-vaapi-driver ];
      };

      nvidia = {
        open = true;
        package = config.boot.kernelPackages.nvidiaPackages.stable;
        modesetting.enable = true;
        powerManagement = {
          enable = true;
          kernelSuspendNotifier = false;
        };
        dynamicBoost.enable = true;
        moduleParams.nvidia = {
          NVreg_EnableS0ixPowerManagement = 1;
          NVreg_DynamicPowerManagement = 0;
        };
      };
    };

    systemd.services = {
      nvidia-suspend-then-hibernate = {
        description = "NVIDIA system suspend-then-hibernate actions";
        path = [ pkgs.kbd ];
        serviceConfig = {
          Type = "oneshot";
          ExecStart = "${driver}/bin/nvidia-sleep.sh 'suspend'";
        };
        before = [ "systemd-suspend-then-hibernate.service" ];
        requiredBy = [ "systemd-suspend-then-hibernate.service" ];
      };

      nvidia-resume = {
        after = [ "systemd-suspend-then-hibernate.service" ];
        requiredBy = [ "systemd-suspend-then-hibernate.service" ];
      };
    };

    environment = {
      etc."systemd/system-sleep/nvidia".source = "${driver}/lib/systemd/system-sleep/nvidia";

      sessionVariables = {
        LIBVA_DRIVER_NAME = "nvidia";
        NVD_BACKEND = "direct";
      };
    };

    programs.firefox.preferences."media.hardware-video-decoding.force-enabled" = true;
  };
}
