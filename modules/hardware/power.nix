{
  config,
  lib,
  ...
}:
let
  cfg = config.custom.power;
in
{
  options.custom.power = {
    enable = lib.mkEnableOption "power profiles, power-off on critical battery and no hibernation";
  };

  config = lib.mkIf cfg.enable {
    powerManagement.cpuFreqGovernor = "powersave";

    services = {
      power-profiles-daemon.enable = true;
      upower = {
        enable = true;
        criticalPowerAction = "PowerOff";
      };
    };

    systemd = {
      sleep.settings.Sleep = {
        AllowHibernation = false;
        AllowSuspendThenHibernate = false;
        AllowHybridSleep = false;
      };
      services.power-profiles-daemon.serviceConfig.ExecStart = [
        ""
        "${config.services.power-profiles-daemon.package}/libexec/power-profiles-daemon --block-driver=amd_pstate"
      ];
    };

    custom = {
      persistence.directories = [ "/var/lib/power-profiles-daemon" ];
      hardening.serviceExposure.power-profiles-daemon = "1.0";
    };
  };
}
