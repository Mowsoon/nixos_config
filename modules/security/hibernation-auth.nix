{ config, lib, ... }:
let
  cfg = config.custom.hibernationAuth;
  patchDir = ../../kernel/patches/hibernation-tpm-auth;
  patches = [
    "0001-tpm-Reserve-PCR-23-for-the-kernel.patch"
    "0002-tpm-Add-a-TPM-resident-key-to-authenticate-hibernati.patch"
    "0003-PM-hibernate-Compute-a-SHA-256-digest-of-the-image-s.patch"
    "0004-PM-hibernate-Authenticate-swap-images-with-the-TPM.patch"
  ];
  kernelVersion = lib.versions.majorMinor config.boot.kernelPackages.kernel.version;
in
{
  options.custom.hibernationAuth = {
    enable = lib.mkEnableOption "hibernation images authenticated by a TPM-resident key, with PCR 23 reserved to the kernel";
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = kernelVersion == "7.2";
        message = "custom.hibernationAuth: the patches target Linux 7.2, the kernel is ${kernelVersion}; rebase kernel/patches/hibernation-tpm-auth first";
      }
    ];

    boot.kernelPatches =
      map (file: {
        name = lib.removeSuffix ".patch" file;
        patch = patchDir + "/${file}";
      }) patches
      ++ [
        {
          name = "hibernation-tpm-auth-config";
          patch = null;
          structuredExtraConfig.HIBERNATION_TPM_AUTH = lib.kernel.yes;
        }
      ];
  };
}
