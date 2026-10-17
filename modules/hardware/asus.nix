{ config, lib, ... }:
let
  cfg = config.custom.asus;
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
  };

  config = lib.mkIf cfg.enable {
    services.asusd.enable = true;

    programs.rog-control-center.enable = true;

    systemd.services.asus-charge-limit = {
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

    custom.persistence.directories = [ "/etc/asusd" ];
  };
}
