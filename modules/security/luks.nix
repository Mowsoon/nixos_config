{ config, lib, ... }:
let
  cfg = config.custom.luks;
in
{
  options.custom.luks = {
    tpm2Unlock = lib.mkEnableOption "the TPM2 unlock of the encrypted root container";

    measureVolumeKey = lib.mkEnableOption "the measurement of the volume key of the root container into PCR 15 at unlock, which binds TPM2-sealed credentials to this container";

    name = lib.mkOption {
      type = lib.types.str;
      default = "cryptroot";
      description = "Name of the LUKS mapping declared by disko.";
    };
  };

  config.boot.initrd = {
    luks.devices.${cfg.name}.crypttabExtraOpts =
      lib.optional cfg.tpm2Unlock "tpm2-device=auto"
      ++ lib.optional cfg.measureVolumeKey "tpm2-measure-pcr=yes";

    systemd.sockets.systemd-pcrextend = lib.mkIf cfg.measureVolumeKey {
      wantedBy = [ "cryptsetup.target" ];
      before = [ "systemd-cryptsetup@${cfg.name}.service" ];
    };
  };
}
