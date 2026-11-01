{ inputs, pkgs, ... }:
{
  imports = [
    inputs.disko.nixosModules.disko
    inputs.impermanence.nixosModules.impermanence
    inputs.lanzaboote.nixosModules.lanzaboote
    "${inputs.disko}/lib/interactive-vm.nix"
    ../../hosts/hephaestus/disko.nix
    ../../hosts/hephaestus/vm.nix
    ../../modules/core/root-rollback.nix
    ../../modules/core/persistence.nix
    ../../modules/security/secure-boot.nix
    ../../modules/security/luks.nix
  ];

  boot.kernelPackages = pkgs.linuxPackages_zen;

  custom = {
    secureBoot.enable = true;

    luks.tpm2Unlock = true;

    rootRollback = {
      enable = true;
      device = "/dev/mapper/cryptroot";
    };

    persistence = {
      enable = true;
      root = "/persist";
    };
  };

  disko.devices.disk.main.imageSize = "8G";

  environment.systemPackages = [ pkgs.tpm2-tools ];

  system.switch.enable = true;

  virtualisation = {
    memorySize = 2048;
    cores = 2;
  };
}
