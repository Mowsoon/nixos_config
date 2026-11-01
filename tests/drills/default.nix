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
        ''
        + builtins.readFile ./helpers.py
        + builtins.readFile ./${name}.py;
    };
in
pkgs.lib.genAttrs [
  "boot"
  "dbx-update"
  "enrollment"
  "rebuild-power-loss"
  "tpm-clear"
] mkDrill
