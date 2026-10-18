{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.custom.nvidia;
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
        moduleParams.nvidia.NVreg_EnableS0ixPowerManagement = 1;
      };
    };

    environment.sessionVariables = {
      LIBVA_DRIVER_NAME = "nvidia";
      NVD_BACKEND = "direct";
    };

    programs.firefox.preferences."media.hardware-video-decoding.force-enabled" = true;
  };
}
