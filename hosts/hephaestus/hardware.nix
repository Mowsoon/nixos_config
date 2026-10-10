{ inputs, pkgs, ... }:
{
  imports = [
    inputs.nixos-hardware.nixosModules.common-cpu-amd-pstate
    inputs.nixos-hardware.nixosModules.common-gpu-nvidia-nonprime
    inputs.nixos-hardware.nixosModules.common-pc-laptop
    ../../modules/hardware/nvidia.nix
    ../../modules/hardware/asus.nix
    ../../modules/hardware/audio.nix
    ../../modules/hardware/peripherals.nix
  ];

  boot = {
    kernelPackages = pkgs.linuxPackages_zen;
    kernelModules = [ "kvm-amd" ];
    initrd.availableKernelModules = [
      "nvme"
      "xhci_pci"
      "usbhid"
    ];
  };

  hardware.enableRedistributableFirmware = true;

  services.power-profiles-daemon.enable = true;

  custom = {
    nvidia.enable = true;
    asus.enable = true;
    audio.enable = true;
    peripherals.enable = true;
    persistence.directories = [ "/var/lib/power-profiles-daemon" ];
  };
}
