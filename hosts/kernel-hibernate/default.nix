{ lib, pkgs, ... }:
let
  scenario = pkgs.writeShellApplication {
    name = "hibernation-scenario";
    runtimeInputs = [
      pkgs.coreutils
      pkgs.gnugrep
      pkgs.gnused
      pkgs.systemd
      pkgs.tpm2-tools
      pkgs.util-linux
    ];
    text = builtins.readFile ./scenario.sh;
  };
in
{
  imports = [ ../vm-test ];

  networking.hostName = lib.mkForce "kernel-hibernate";

  services.getty.autologinUser = "root";

  systemd.services.hibernation-scenario = {
    wantedBy = [ "multi-user.target" ];
    unitConfig.ConditionKernelCommandLine = "hibernation_test";
    serviceConfig = {
      Type = "oneshot";
      ExecStart = lib.getExe scenario;
    };
  };

  environment.systemPackages = [ pkgs.tpm2-tools ];

  virtualisation = {
    useNixStoreImage = true;
    sharedDirectories = lib.mkForce { };
    tpm.enable = true;
    qemu.drives = [
      {
        name = "hibernate-swap";
        file = ''"$KERNEL_HIBERNATE_SWAP"'';
        driveExtraOpts.format = "raw";
        deviceExtraOpts.serial = "hibernate-swap";
      }
    ];
  };
}
