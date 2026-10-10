{ config, lib, ... }:
let
  cfg = config.custom.luks;
in
{
  options.custom.luks = {
    tpm2Unlock = lib.mkEnableOption "the TPM2 unlock of the encrypted root container";

    name = lib.mkOption {
      type = lib.types.str;
      default = "cryptroot";
      description = "Name of the LUKS mapping declared by disko.";
    };
  };

  config = lib.mkIf cfg.tpm2Unlock {
    boot.initrd.luks.devices.${cfg.name}.crypttabExtraOpts = [ "tpm2-device=auto" ];
  };
}
