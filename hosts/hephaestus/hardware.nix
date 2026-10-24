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
    ../../modules/hardware/rgb.nix
    ../../modules/hardware/power.nix
    ../../modules/hardware/disk-health.nix
    ../../modules/hardware/mt7921.nix
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

  custom = {
    nvidia.enable = true;
    asus = {
      enable = true;
      chargeLimit = 80;
      performanceEpp = "BalancePerformance";
    };
    audio = {
      enable = true;
      serializeAmdAcpResume = true;
    };
    peripherals.enable = true;
    rgb = {
      enable = true;
      effects = {
        enable = true;
        keys.enable = true;
      };
    };
    power = {
      enable = true;
      disarmInputWakeupForHibernation = true;
    };
    diskHealth.enable = true;
    mt7921.enable = true;
  };
}
