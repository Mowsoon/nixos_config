{ config, lib, ... }:
let
  cfg = config.custom.audio;
in
{
  options.custom.audio = {
    enable = lib.mkEnableOption "PipeWire as the audio server for ALSA, PulseAudio and JACK clients";
  };

  config = lib.mkIf cfg.enable {
    security.rtkit.enable = true;

    services.pipewire = {
      enable = true;
      alsa = {
        enable = true;
        support32Bit = true;
      };
      pulse.enable = true;
      jack.enable = true;
    };
  };
}
