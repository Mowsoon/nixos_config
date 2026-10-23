{ config, lib, ... }:
let
  cfg = config.custom.network.dns;
in
{
  options.custom.network.dns = {
    enable = lib.mkEnableOption "systemd-resolved with Quad9 over TLS and split DNS for local networks";
  };

  config = lib.mkIf cfg.enable {
    services.resolved = {
      enable = true;
      settings.Resolve = {
        DNS = [
          "9.9.9.9#dns.quad9.net"
          "149.112.112.112#dns.quad9.net"
          "2620:fe::fe#dns.quad9.net"
          "2620:fe::9#dns.quad9.net"
        ];
        DNSOverTLS = true;
        Domains = [ "~." ];
        FallbackDNS = [ ];
        LLMNR = false;
        MulticastDNS = false;
      };
    };

    networking.networkmanager.connectionConfig."connection.dns-over-tls" = 0;

    systemd = {
      services.resolved-reset-server-features = {
        description = "Retry the DNS servers after a clock change";
        serviceConfig = {
          Type = "oneshot";
          ExecStart = "${config.systemd.package}/bin/resolvectl reset-server-features";
        };
      };
      timers.resolved-reset-server-features = {
        wantedBy = [ "timers.target" ];
        timerConfig.OnClockChange = true;
      };
    };

    custom.network.opensnitch.allowedExecutables.systemd-resolved =
      "${config.systemd.package}/lib/systemd/systemd-resolved";
  };
}
