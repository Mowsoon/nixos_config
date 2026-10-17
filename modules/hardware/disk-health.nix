{ config, lib, ... }:
let
  cfg = config.custom.diskHealth;
in
{
  options.custom.diskHealth = {
    enable = lib.mkEnableOption "SMART monitoring of every detected disk with desktop notifications";
  };

  config = lib.mkIf cfg.enable {
    services.smartd = {
      enable = true;
      autodetect = true;
      notifications.systembus-notify.enable = true;
    };
  };
}
