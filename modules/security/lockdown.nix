{
  config,
  lib,
  options,
  pkgs,
  ...
}:
let
  cfg = config.custom.lockdown;
  inherit (config.boot.kernelPackages) kernel;
  target = config.system.boot.loader.kernelFile;
  modulesDir = "lib/modules/${kernel.modDirVersion}";
  certificates = pkgs.runCommand "module-certificates-${kernel.version}" { } ''
    mkdir -p $out/${modulesDir}
    cd ${config.system.modulesTree}/${modulesDir}
    {
      cat ${lib.getOutput "modules" kernel}/${modulesDir}/modules.cer
      find -L . -name '*.ko.cer' -print0 | sort -z | xargs -0 -r cat
    } > $out/${modulesDir}/modules.cer
  '';
  image = config.boot.kernelPackages.rebuildImage {
    inherit target;
    modulesTree = certificates;
  };
  kernelPath = "${image}/${target}";
  jq = lib.getExe pkgs.buildPackages.jq;
  bootspec = "$out/${config.boot.bootspec.filename}";
in
{
  options.custom.lockdown = {
    moduleCertificates = lib.mkEnableOption "the insertion of the kmodigest module certificates into the kernel image, so that the kernel verifies the signature of every module it loads";
  };

  config = lib.mkIf cfg.moduleCertificates {
    boot.bootspec.writer = lib.mkForce ''
      ${options.boot.bootspec.writer.default}
      ${jq} --sort-keys --arg kernel ${kernelPath} '."org.nixos.bootspec.v1".kernel = $kernel' \
        ${bootspec} > ${bootspec}.new
      mv ${bootspec}.new ${bootspec}
    '';

    system.systemBuilderCommands = lib.mkAfter ''
      ln -sfn ${kernelPath} $out/kernel
    '';
  };
}
