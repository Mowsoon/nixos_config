{ lib, testers }:
testers.runNixOSTest {
  name = "kernel-vm-modules";
  node.pkgsReadOnly = false;
  nodes.machine = {
    imports = [ ../hosts/kernel-test ];
    virtualisation.sharedDirectories.kernel.source = lib.mkForce "$TMPDIR";
  };
  testScript = ''
    import os

    machine.wait_for_unit("multi-user.target")
    os.makedirs(os.environ["out"], exist_ok=True)
    with open(os.path.join(os.environ["out"], "lsmod"), "w") as lsmod:
        lsmod.write(machine.succeed("lsmod"))
  '';
}
