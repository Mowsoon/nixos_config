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

    custom.network.opensnitch.allowedExecutables.systemd-resolved =
      "${config.systemd.package}/lib/systemd/systemd-resolved";
  };
}
