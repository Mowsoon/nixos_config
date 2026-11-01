{ lib, ... }:
{
  imports = [ ../vm-test ];

  networking.hostName = lib.mkForce "kernel-test";

  services.getty.autologinUser = "root";

  virtualisation.sharedDirectories.kernel = {
    source = "$KERNEL_TREE";
    target = "/src";
  };
}
