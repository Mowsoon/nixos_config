{ config, lib, ... }:
let
  cfg = config.custom.audio;
in
{
  options.custom.audio = {
    enable = lib.mkEnableOption "PipeWire as the audio server for ALSA, PulseAudio and JACK clients";
    serializeAmdAcpResume = lib.mkEnableOption "sequential suspend and resume of the AMD revision 0x62 audio coprocessor and HD Audio controller";
  };

  config = lib.mkIf cfg.enable {
    security.rtkit.enable = true;

    services = {
      pipewire = {
        enable = true;
        alsa = {
          enable = true;
          support32Bit = true;
        };
        pulse.enable = true;
        jack.enable = true;
      };

      udev.extraRules = lib.mkIf cfg.serializeAmdAcpResume ''
        ACTION=="add", SUBSYSTEM=="pci", ATTR{vendor}=="0x1022", ATTR{device}=="0x15e2", ATTR{revision}=="0x62", ATTR{power/async}="disabled"
        ACTION=="add", SUBSYSTEM=="pci", ATTR{vendor}=="0x1022", ATTR{device}=="0x15e3", ATTR{power/async}="disabled"
      '';
    };
  };
}
