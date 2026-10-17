{ config, lib, ... }:
let
  cfg = config.custom.memory;
in
{
  options.custom.memory = {
    enable = lib.mkEnableOption "compressed swap in RAM tuned for zram and oomd on user sessions";
  };

  config = lib.mkIf cfg.enable {
    zramSwap = {
      enable = true;
      algorithm = "zstd";
      memoryPercent = 50;
      priority = 100;
    };

    boot = {
      kernelParams = [ "zswap.enabled=0" ];
      kernel.sysctl = {
        "vm.swappiness" = 180;
        "vm.page-cluster" = 0;
      };
    };

    systemd.oomd.enableUserSlices = true;
  };
}
