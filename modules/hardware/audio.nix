{ config, lib, ... }:
let
  cfg = config.custom.audio;
in
{
  options.custom.audio = {
    enable = lib.mkEnableOption "PipeWire as the audio server for ALSA, PulseAudio and JACK clients";
    serializeAmdAcpResume = lib.mkEnableOption "sequential suspend and resume of the AMD revision 0x62 audio coprocessor and HD Audio controller";
    deferCs35l41FirmwareReload = lib.mkEnableOption "the kernel patch that queues the CS35L41 amplifier firmware reload of system resume on a freezable workqueue, so hibernation powers off";
  };

  config = lib.mkIf cfg.enable {
    boot.kernelPatches = lib.mkIf cfg.deferCs35l41FirmwareReload [
      {
        name = "cs35l41-freezable-fw-load";
        patch = ../../kernel/patches/cs35l41-freezable-fw-load/0001-ALSA-hda-cs35l41-Queue-the-resume-firmware-load-on-a.patch;
      }
    ];

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
