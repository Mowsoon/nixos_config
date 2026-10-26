{ config, lib, ... }:
let
  cfg = config.custom.peripherals;
in
{
  options.custom.peripherals = {
    enable = lib.mkEnableOption "Bluetooth, Logitech receivers and the G915 X key remapping";
  };

  config = lib.mkIf cfg.enable {
    hardware = {
      bluetooth = {
        enable = true;
        settings.General.Experimental = true;
      };
      logitech.wireless.enable = true;
    };

    services.udev.extraHwdb = ''
      evdev:input:b0003v046Dp40B5*
      evdev:input:b0003v046DpC356*
       KEYBOARD_KEY_70068=f14
       KEYBOARD_KEY_70069=f15
       KEYBOARD_KEY_7006a=f16
       KEYBOARD_KEY_7006b=f17
       KEYBOARD_KEY_7006c=f18
       KEYBOARD_KEY_7006d=scale
       KEYBOARD_KEY_7006e=dashboard
       KEYBOARD_KEY_7006f=finance
       KEYBOARD_KEY_70070=shop
    '';

    custom.persistence.directories = [ "/var/lib/bluetooth" ];
  };
}
