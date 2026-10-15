{
  inputs,
  modulesPath,
  pkgs,
  ...
}:
{
  imports = [ "${modulesPath}/installer/cd-dvd/installation-cd-minimal.nix" ];

  nixpkgs.hostPlatform = "x86_64-linux";

  nix.settings.experimental-features = [
    "nix-command"
    "flakes"
  ];

  console.keyMap = "fr";

  zramSwap.enable = true;

  environment.systemPackages = with pkgs; [
    age
    efibootmgr
    git
    mkpasswd
    sbctl
    inputs.disko.packages.${pkgs.stdenv.hostPlatform.system}.disko
  ];
}
