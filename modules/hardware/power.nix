{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.custom.power;
  inputWakeupHook = pkgs.writeShellScript "hibernate-input-wakeup" ''
    export PATH=${
      lib.makeBinPath [
        pkgs.coreutils
        pkgs.gnugrep
      ]
    }
    state=/run/hibernate-input-wakeup
    case "$1:''${SYSTEMD_SLEEP_ACTION:-$2}" in
      pre:hibernate)
        : > "$state"
        for dev in /sys/bus/usb/devices/*; do
          [ -f "$dev/power/wakeup" ] || continue
          [ "$(cat "$dev/power/wakeup")" = enabled ] || continue
          grep -qx 03 "$dev"/*/bInterfaceClass 2>/dev/null || continue
          echo disabled > "$dev/power/wakeup"
          echo "$dev" >> "$state"
        done
        ;;
      post:*)
        [ -f "$state" ] || exit 0
        while read -r dev; do
          [ -f "$dev/power/wakeup" ] && echo enabled > "$dev/power/wakeup"
        done < "$state"
        rm -f "$state"
        ;;
    esac
  '';
in
{
  options.custom.power = {
    enable = lib.mkEnableOption "power profiles, delayed hibernation after sleep and hibernation on critical battery";
    disarmInputWakeupForHibernation = lib.mkEnableOption "USB keyboards and mice kept from waking the machine while it enters hibernation";
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

    environment.etc = lib.mkIf cfg.disarmInputWakeupForHibernation {
      "systemd/system-sleep/hibernate-input-wakeup".source = inputWakeupHook;
    };

    custom.persistence.directories = [ "/var/lib/power-profiles-daemon" ];
  };
}
