{ config, lib, ... }:
let
  cfg = config.custom.peripherals;
in
{
  options.custom.peripherals = {
    enable = lib.mkEnableOption "Bluetooth and input remapping for external peripherals";
  };

  config = lib.mkIf cfg.enable {
    hardware.bluetooth.enable = true;

    services.input-remapper.enable = true;

    custom.persistence.directories = [ "/var/lib/bluetooth" ];
  };
}
