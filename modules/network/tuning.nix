{ config, lib, ... }:
let
  cfg = config.custom.network.tuning;
in
{
  options.custom.network.tuning = {
    enable = lib.mkEnableOption "the BBR congestion control with the fq queueing discipline";
  };

  config = lib.mkIf cfg.enable {
    boot = {
      kernelModules = [ "tcp_bbr" ];
      kernel.sysctl = {
        "net.core.default_qdisc" = "fq";
        "net.ipv4.tcp_congestion_control" = "bbr";
      };
    };
  };
}
