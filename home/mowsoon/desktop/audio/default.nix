{
  services.easyeffects = {
    enable = true;
    extraPresets.microphone = builtins.fromJSON (builtins.readFile ./microphone.json);
    preset.input = "microphone";
  };
}
