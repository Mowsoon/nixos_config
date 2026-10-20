{
  services.easyeffects = {
    enable = true;
    extraPresets.microphone = builtins.fromJSON (builtins.readFile ./audio/microphone.json);
    preset.input = "microphone";
  };
}
