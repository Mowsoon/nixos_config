{ lib, ... }:
{
  imports = [ ../vm-test ];

  networking.hostName = lib.mkForce "kernel-test";

  services.getty.autologinUser = "root";

  systemd.targets.multi-user.wants = [ "kernel-command-line.service" ];

  virtualisation.sharedDirectories.kernel = {
    source = "$KERNEL_TREE";
    target = "/src";
    writable = true;
  };
}
