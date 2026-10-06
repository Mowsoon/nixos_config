{ lib, modulesPath, ... }:
{
  imports = [ "${modulesPath}/virtualisation/qemu-vm.nix" ];

  nixpkgs.hostPlatform = "x86_64-linux";

  networking.hostName = "vm-test";

  nix.settings.experimental-features = [
    "nix-command"
    "flakes"
  ];

  console.keyMap = "fr";
  time.timeZone = "Europe/Paris";
  i18n.defaultLocale = "en_US.UTF-8";

  users.mutableUsers = false;
  users.users.mowsoon = {
    isNormalUser = true;
    extraGroups = [ "wheel" ];
    hashedPassword = lib.fileContents ./mowsoon.hash;
  };

  virtualisation = {
    memorySize = 4096;
    cores = 4;
    graphics = false;
  };

  system.stateVersion = "26.11";
}
