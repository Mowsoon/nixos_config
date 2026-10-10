{ config, lib, ... }:
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
      };

      nvidia = {
        open = true;
        package = config.boot.kernelPackages.nvidiaPackages.stable;
        modesetting.enable = true;
        powerManagement.enable = true;
        dynamicBoost.enable = true;
      };
    };
  };
}
