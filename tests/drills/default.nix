{ pkgs, inputs }:
let
  mkDrill =
    name:
    pkgs.testers.runNixOSTest {
      name = "drill-${name}";
      node.specialArgs = { inherit inputs; };
      nodes.machine = ./node.nix;
      testScript =
        { nodes, ... }:
        ''
          disko_image = "${nodes.machine.system.build.diskoImages}/main.qcow2"
          qemu_img = "${nodes.machine.virtualisation.qemu.package}/bin/qemu-img"
          next_system = "${nodes.machine.system.build.drillNextGeneration}"
          other_firmware_vm = "${nodes.machine.system.build.drillOtherFirmwareVm}/bin/run-machine-vm"
        ''
        + builtins.readFile ./helpers.py
        + builtins.readFile ./${name}.py;
    };
in
pkgs.lib.genAttrs [
  "boot"
  "credential-injection"
  "dbx-update"
  "enrollment"
  "firmware-update"
  "rebuild-power-loss"
  "tpm-clear"
] mkDrill
