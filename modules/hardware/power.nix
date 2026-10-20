{ config, lib, ... }:
let
  cfg = config.custom.power;
in
{
  options.custom.power = {
    enable = lib.mkEnableOption "power profiles, delayed hibernation after sleep and hibernation on critical battery";
  };

  config = lib.mkIf cfg.enable {
    powerManagement.cpuFreqGovernor = "powersave";

    services = {
      power-profiles-daemon.enable = true;
      upower = {
        enable = true;
        criticalPowerAction = "Hibernate";
      };
    };

    systemd = {
      sleep.settings.Sleep.HibernateDelaySec = "2h";
      services.power-profiles-daemon.serviceConfig.ExecStart = [
        ""
        "${config.services.power-profiles-daemon.package}/libexec/power-profiles-daemon --block-driver=amd_pstate"
      ];
    };

    custom.persistence.directories = [ "/var/lib/power-profiles-daemon" ];
  };
}
