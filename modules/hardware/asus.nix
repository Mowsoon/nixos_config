{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.custom.asus;
  asusdConfig = "/etc/asusd/asusd.ron";
  enforcePerformanceEpp = pkgs.writeShellScript "asusd-performance-epp" ''
    if [ ! -e ${asusdConfig} ]; then
      exit 0
    fi
    if ! ${pkgs.gnugrep}/bin/grep -q '^    profile_performance_epp: [A-Za-z]*,$' ${asusdConfig}; then
      echo "profile_performance_epp not found in ${asusdConfig}" >&2
      exit 1
    fi
    ${pkgs.gnused}/bin/sed -i 's/^\(    profile_performance_epp: \)[A-Za-z]*,$/\1${cfg.performanceEpp},/' ${asusdConfig}
  '';
in
{
  options.custom.asus = {
    enable = lib.mkEnableOption "the ASUS platform daemon for fans, profiles, keyboard backlight and charge limit";

    chargeLimit = lib.mkOption {
      type = lib.types.ints.between 20 100;
      default = 100;
      example = 80;
      description = "Battery charge percentage at which charging stops, applied through asusd at boot.";
    };

    performanceEpp = lib.mkOption {
      type = lib.types.nullOr (
        lib.types.enum [
          "Default"
          "Performance"
          "BalancePerformance"
          "BalancePower"
          "Power"
        ]
      );
      default = null;
      example = "BalancePerformance";
      description = "Energy performance preference that asusd writes with the Performance profile, enforced in its configuration before it starts. Null leaves asusd's own value.";
    };
  };

  config = lib.mkIf cfg.enable {
    services.asusd.enable = true;

    programs.rog-control-center.enable = true;

    systemd.services = {
      asusd = lib.mkIf (cfg.performanceEpp != null) {
        after = [ "cpufreq.service" ];
        serviceConfig.ExecStartPre = [ "+${enforcePerformanceEpp}" ];
      };

      asus-charge-limit = {
        description = "Apply the declared battery charge limit through asusd";
        wantedBy = [ "multi-user.target" ];
        requires = [ "asusd.service" ];
        after = [ "asusd.service" ];
        serviceConfig = {
          Type = "oneshot";
          RemainAfterExit = true;
          ExecStart = "${config.services.asusd.package}/bin/asusctl battery limit ${toString cfg.chargeLimit}";
        };
      };
    };

    custom.persistence.directories = [ "/etc/asusd" ];
  };
}
