{ config, lib, ... }:
let
  cfg = config.custom.network.time;
in
{
  options.custom.network.time = {
    enable = lib.mkEnableOption "time synchronisation authenticated with NTS through chrony";
  };

  config = lib.mkIf cfg.enable {
    services.chrony = {
      enable = true;
      enableNTS = true;
      servers = [
        "time.cloudflare.com"
        "nts.netnod.se"
        "ptbtime1.ptb.de"
        "ptbtime2.ptb.de"
      ];
      extraConfig = "nocerttimecheck 1";
    };

    custom = {
      network.opensnitch.allowedExecutables.chronyd = "${config.services.chrony.package}/bin/chronyd";
      persistence.directories = [
        {
          directory = config.services.chrony.directory;
          user = "chrony";
          group = "chrony";
          mode = "0750";
        }
      ];
    };
  };
}
