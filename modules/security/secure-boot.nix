{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.custom.secureBoot;
  lanzaboote = config.boot.lanzaboote;
  systemd = config.systemd.package;
  esp = config.boot.loader.efi.efiSysMountPoint;
  unsealed = "/run/secure-boot-keys";
  keyDirectory = if cfg.sealedKeys then unsealed else cfg.pkiBundle;
  keys = [
    "PK"
    "KEK"
    "db"
  ];
  secureBootKeys = pkgs.writeShellApplication {
    name = "secure-boot-keys";
    runtimeInputs = [
      pkgs.coreutils
      pkgs.diffutils
      pkgs.sbctl
      systemd
    ];
    text = ''
      pki=${cfg.pkiBundle}
      run=${unsealed}
      keys=(${lib.concatStringsSep " " keys})

      seal() {
        if [ "$(tr -d '0\n' < /sys/class/tpm/tpm0/pcr-sha256/15)" = "" ]; then
          echo "PCR 15 is zero: the volume key of the root container is not measured" >&2
          exit 1
        fi
        for key in "''${keys[@]}"; do
          plain="$pki/keys/$key/$key.key"
          sealed="$plain.cred"
          systemd-creds encrypt --with-key=tpm2 --tpm2-pcrs=15 --name="secure-boot-$key.key" "$plain" "$sealed.tmp"
          systemd-creds decrypt --name="secure-boot-$key.key" "$sealed.tmp" - | cmp - "$plain"
          chmod 0400 "$sealed.tmp"
          mv "$sealed.tmp" "$sealed"
          echo "sealed $plain to $sealed"
        done
      }

      unseal() {
        rm -rf "$run"
        install -d -m 0700 "$run" "$run/keys"
        if [ ! -e "$pki/GUID" ]; then
          echo "no Secure Boot keys in $pki yet, the boot loader is installed unsigned" >&2
          return
        fi
        cp "$pki/GUID" "$run/GUID"
        {
          printf 'keydir: %s\nguid: %s\nkeys:\n' "$run/keys" "$run/GUID"
          for key in "''${keys[@]}"; do
            printf '  %s:\n    privkey: %s\n    pubkey: %s\n    type: file\n' \
              "''${key,,}" "$run/keys/$key/$key.key" "$run/keys/$key/$key.pem"
          done
        } > "$run/sbctl.conf"
        for key in "''${keys[@]}"; do
          install -d -m 0700 "$run/keys/$key"
          cp "$pki/keys/$key/$key.pem" "$run/keys/$key/$key.pem"
          if [ -e "$pki/keys/$key/$key.key" ]; then
            install -m 0400 "$pki/keys/$key/$key.key" "$run/keys/$key/$key.key"
          else
            (umask 0077; systemd-creds decrypt --name="secure-boot-$key.key" "$pki/keys/$key/$key.key.cred" "$run/keys/$key/$key.key")
          fi
        done
      }

      wipe() {
        rm -rf "$run"
      }

      with_keys() {
        unseal
        trap wipe EXIT
        sbctl --config "$run/sbctl.conf" "$@"
      }

      case "''${1:-}" in
        seal) seal ;;
        unseal) unseal ;;
        wipe) wipe ;;
        sbctl)
          shift
          with_keys "$@"
          ;;
        *)
          echo "usage: secure-boot-keys seal|unseal|wipe|sbctl <arguments>" >&2
          exit 2
          ;;
      esac
    '';
  };
  installBootLoader = pkgs.writeShellScript "install-boot-loader" ''
    set -e
    PATH=${systemd}/lib/systemd:$PATH
    ${lib.optionalString cfg.sealedKeys ''
      ${lib.getExe secureBootKeys} unseal
      trap '${lib.getExe secureBootKeys} wipe' EXIT
    ''}
    ${lanzaboote.installCommand} \
      ${
        lib.escapeShellArgs [
          "--public-key=${keyDirectory}/keys/db/db.pem"
          "--private-key=${keyDirectory}/keys/db/db.key"
          esp
        ]
      } /nix/var/nix/profiles/system-*-link
    ${lib.optionalString cfg.sealedKeys ''
      ${lib.getExe secureBootKeys} wipe
      trap - EXIT
    ''}
    ${cfg.postInstallCommands}
  '';
in
{
  options.custom.secureBoot = {
    enable = lib.mkEnableOption "Secure Boot signing of the boot chain with lanzaboote";

    pkiBundle = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/sbctl";
      description = "Directory holding the Secure Boot keys already enrolled in the firmware.";
    };

    sealedKeys = lib.mkEnableOption "Secure Boot private keys stored as TPM2-sealed credentials bound to PCR 15, decrypted in memory only while the boot loader is installed";

    postInstallCommands = lib.mkOption {
      type = lib.types.lines;
      default = "";
      description = "Shell commands that the boot loader install hook runs after lanzaboote installed the generations, set by other modules.";
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = !lanzaboote.measuredBoot.enable && lanzaboote.extraEfiSysMountPoints == [ ];
        message = "custom.secureBoot replaces the install hook of lanzaboote, which then must use one ESP and no measured boot of its own";
      }
    ];

    boot = {
      lanzaboote = {
        enable = true;
        inherit (cfg) pkiBundle;
        configurationLimit = 8;
      };
      loader.external.installHook = lib.mkForce "${installBootLoader}";
    };

    custom.persistence.directories = [ cfg.pkiBundle ];

    environment.systemPackages = [ pkgs.sbctl ] ++ lib.optional cfg.sealedKeys secureBootKeys;
  };
}
