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
      enableRTCTrimming = false;
      makestep.enable = false;
      extraConfig = ''
        nocerttimecheck 1
        rtcsync
        makestep 1 -1
      '';
    };

    networking.hosts = {
      "162.159.200.1" = [ "time.cloudflare.com" ];
      "162.159.200.123" = [ "time.cloudflare.com" ];
      "2606:4700:f1::1" = [ "time.cloudflare.com" ];
      "2606:4700:f1::123" = [ "time.cloudflare.com" ];
      "192.53.103.108" = [ "ptbtime1.ptb.de" ];
      "2001:638:610:be01::108" = [ "ptbtime1.ptb.de" ];
      "192.53.103.104" = [ "ptbtime2.ptb.de" ];
      "2001:638:610:be01::104" = [ "ptbtime2.ptb.de" ];
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
