{ config, lib, ... }:
let
  cfg = config.custom.network.firewall;
in
{
  options.custom.network.firewall = {
    enable = lib.mkEnableOption "the stateful nftables firewall";
  };

  config = lib.mkIf cfg.enable {
    networking = {
      nftables.enable = true;
      firewall.enable = true;
    };
  };
}
