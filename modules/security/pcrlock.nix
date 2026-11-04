{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.custom.pcrlock;
  systemd = config.systemd.package;
  separator = "500-separator.pcrlock.d/300-0x00000000.pcrlock";
  policy = "/var/lib/systemd/pcrlock.json";
  makePolicy = pkgs.writeShellScriptBin "pcrlock-make-policy" ''
    exec ${systemd}/lib/systemd/systemd-pcrlock make-policy --location=770 --strict=true ${
      lib.concatMapStringsSep " " (pcr: "--pcr=${toString pcr}") cfg.pcrs
    } "$@"
  '';
in
{
  options.custom.pcrlock = {
    enable = lib.mkEnableOption "the systemd-pcrlock policy that locks the TPM2 unlock to the firmware code";

    pcrs = lib.mkOption {
      type = lib.types.listOf (lib.types.ints.between 0 23);
      default = [ 0 ];
      description = "PCRs covered by the policy; the policy update fails when one of them cannot be predicted.";
    };
  };

  config = lib.mkIf cfg.enable {
    environment = {
      etc."pcrlock.d/${separator}".source = "${systemd}/lib/pcrlock.d/${separator}";
      systemPackages = [ makePolicy ];
    };

    systemd = {
      additionalUpstreamSystemUnits = [
        "systemd-pcrlock-firmware-code.service"
        "systemd-pcrlock-make-policy.service"
      ];

      services = {
        systemd-pcrlock-firmware-code = {
          wantedBy = [ "sysinit.target" ];
          unitConfig.RequiresMountsFor = [ "/var/lib/pcrlock.d" ];
        };

        systemd-pcrlock-make-policy = {
          wantedBy = [ "sysinit.target" ];
          unitConfig = {
            ConditionPathExists = policy;
            RequiresMountsFor = [
              "/var/lib/pcrlock.d"
              "/var/lib/systemd"
              config.boot.loader.efi.efiSysMountPoint
            ];
          };
          serviceConfig.ExecStart = [
            ""
            (lib.getExe makePolicy)
          ];
        };
      };
    };

    custom = {
      persistence.directories = [ "/var/lib/pcrlock.d" ];
      hardening.serviceExposure = {
        systemd-pcrlock-firmware-code = "9.4";
        systemd-pcrlock-make-policy = "9.4";
      };
    };
  };
}
