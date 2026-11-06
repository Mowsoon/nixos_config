{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.custom.pcrlock;
  lanzaboote = config.boot.lanzaboote;
  systemd = config.systemd.package;
  esp = config.boot.loader.efi.efiSysMountPoint;
  separator = "500-separator.pcrlock.d/300-0x00000000.pcrlock";
  exitBootServices = "700-action-efi-exit-boot-services.pcrlock.d";
  bootLoaderConfigRecord = action: {
    pcr = 5;
    digests = [
      {
        hashAlg = "sha256";
        digest = builtins.hashString "sha256" "Exit Boot Services ${action}";
      }
    ];
  };
  exitBootServicesVariants =
    lib.mapAttrs (_: actions: builtins.toJSON { records = map bootLoaderConfigRecord actions; })
      {
        "400-success" = [
          "Invocation"
          "Returned with Success"
        ];
        "300-retried" = [
          "Invocation"
          "Returned with Failure"
          "Invocation"
          "Returned with Success"
        ];
        "600-absent" = [ ];
      };
  readsEsp = lib.elem 5 cfg.pcrs || lib.elem 11 cfg.pcrs;
  componentWriter = pkgs.callPackage ../../pkgs/pcrlock-esp/package.nix { };
  writeComponents = lib.escapeShellArgs [
    (lib.getExe componentWriter)
    "--esp=${esp}"
    "--esp-device=${config.fileSystems.${esp}.device}"
    "--pcrlock=${systemd}/lib/systemd/systemd-pcrlock"
  ];
  policy = "/var/lib/systemd/pcrlock.json";
  alertFile = "/run/pcr12/alert";
  predictor = pkgs.callPackage ../../pkgs/pcr0-predict/package.nix { };
  resealer = pkgs.callPackage ../../pkgs/pcr12/package.nix { inherit systemd; };
  pcr12 = "${lib.getExe resealer} --esp=${esp} --mapping=/dev/mapper/${config.custom.luks.name}";
  pcrlock = pkgs.runCommand "systemd-pcrlock" { } ''
    mkdir -p $out/bin
    ln -s ${systemd}/lib/systemd/systemd-pcrlock $out/bin/systemd-pcrlock
  '';
  staticComponents = pkgs.linkFarm "pcrlock.d" (
    [
      {
        name = separator;
        path = "${systemd}/lib/pcrlock.d/${separator}";
      }
    ]
    ++ lib.optionals (lib.elem 5 cfg.pcrs) (
      lib.mapAttrsToList (variant: text: {
        name = "${exitBootServices}/${variant}.pcrlock";
        path = pkgs.writeText "${variant}.pcrlock" text;
      }) exitBootServicesVariants
    )
  );
  makePolicyCommand = "${lib.getExe' pcrlock "systemd-pcrlock"} make-policy --location=770 --strict=true --components=${staticComponents} --components=/var/lib/pcrlock.d ${
    lib.concatMapStringsSep " " (pcr: "--pcr=${toString pcr}") cfg.pcrs
  }";
  makePolicy = pkgs.writeShellScriptBin "pcrlock-make-policy" (
    lib.optionalString readsEsp ''
      ${writeComponents} || exit
    ''
    + (
      if cfg.lockCredentials then
        ''
          ${makePolicyCommand} "$@" && exec ${pcr12} reseal
        ''
      else
        ''
          exec ${makePolicyCommand} "$@"
        ''
    )
  );
  installBootLoader = pkgs.writeShellScript "install-boot-loader" ''
    set -e
    PATH=${systemd}/lib/systemd:$PATH
    ${lanzaboote.installCommand} \
      ${
        lib.escapeShellArgs [
          "--public-key=${toString lanzaboote.publicKeyFile}"
          "--private-key=${toString lanzaboote.privateKeyFile}"
          esp
        ]
      } /nix/var/nix/profiles/system-*-link
    if [ -e ${policy} ]; then
      ${lib.getExe makePolicy}
    fi
  '';
  pcr12Command = pkgs.writeShellScriptBin "pcr12" ''
    exec ${pcr12} "$@"
  '';
  recordFailure = pkgs.writeShellScript "pcr12-record-failure" ''
    if [ "$SERVICE_RESULT" != success ]; then
      ${lib.getExe' pkgs.coreutils "mkdir"} -p ${dirOf alertFile}
      echo "$1" >> ${alertFile}
    fi
  '';
  notify = pkgs.writeShellScript "pcr12-notify" ''
    units=$(${lib.getExe' pkgs.coreutils "sort"} -u ${alertFile} | ${lib.getExe' pkgs.coreutils "tr"} '\n' ' ')
    exec ${lib.getExe' pkgs.libnotify "notify-send"} --urgency=critical --app-name="TPM2 seal" \
      --icon=security-low "TPM2 seal not updated" \
      "The next boot may ask for the recovery key. Failed: $units. Read: journalctl -b -u pcr12-check -u systemd-pcrlock-make-policy"
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

    lockCredentials = lib.mkEnableOption "the seal of the TPM2 slot to PCR 12, the boot credentials of the ESP, renewed after each policy change";
  };

  config = lib.mkIf cfg.enable (
    lib.mkMerge [
      {
        assertions = [
          {
            assertion = !lanzaboote.measuredBoot.enable && lanzaboote.extraEfiSysMountPoints == [ ];
            message = "custom.pcrlock replaces the install hook of lanzaboote, which then must use one ESP and no measured boot of its own";
          }
        ];

        boot.loader.external.installHook = lib.mkForce "${installBootLoader}";

        environment = {
          etc."pcrlock.d".source = staticComponents;
          systemPackages = [
            pcrlock
            makePolicy
            predictor
          ];
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
                  esp
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
      }

      (lib.mkIf cfg.lockCredentials {
        environment.systemPackages = [ pcr12Command ];

        systemd = {
          services = {
            pcr12-check = {
              description = "Check that PCR 12 is reproduced from the ESP credentials";
              wantedBy = [ "sysinit.target" ];
              after = [
                "systemd-tpm2-setup.service"
                "systemd-remount-fs.service"
              ];
              before = [
                "sysinit.target"
                "shutdown.target"
                "systemd-pcrlock-make-policy.service"
              ];
              conflicts = [ "shutdown.target" ];
              unitConfig = {
                DefaultDependencies = false;
                ConditionPathExists = "!/etc/initrd-release";
                ConditionSecurity = "measured-uki";
                RequiresMountsFor = [ esp ];
              };
              serviceConfig = {
                Type = "oneshot";
                RemainAfterExit = true;
                ExecStart = "${pcr12} check";
                ExecStopPost = "${recordFailure} %n";
                RuntimeDirectory = "pcr12";
                RuntimeDirectoryPreserve = true;
                UMask = "0077";
                CapabilityBoundingSet = "";
                NoNewPrivileges = true;
                ProtectSystem = "strict";
                ProtectHome = true;
                PrivateTmp = "disconnected";
                PrivateDevices = true;
                PrivateNetwork = true;
                IPAddressDeny = "any";
                RestrictAddressFamilies = "none";
                ProtectKernelTunables = true;
                ProtectKernelModules = true;
                ProtectKernelLogs = true;
                ProtectControlGroups = true;
                ProtectClock = true;
                ProtectHostname = true;
                RestrictNamespaces = true;
                RestrictRealtime = true;
                RestrictSUIDSGID = true;
                LockPersonality = true;
                MemoryDenyWriteExecute = true;
                SystemCallArchitectures = "native";
                SystemCallFilter = [ "@system-service" ];
              };
            };

            systemd-pcrlock-make-policy = {
              wants = [ "pcr12-check.service" ];
              after = [ "pcr12-check.service" ];
              unitConfig.RequiresMountsFor = [ "/var/lib/pcr12" ];
              serviceConfig.ExecStopPost = "${recordFailure} %n";
            };
          };

          user = {
            services.pcr12-alert = {
              description = "Report a TPM2 seal that could not be renewed";
              wantedBy = [ "graphical-session.target" ];
              after = [ "graphical-session.target" ];
              unitConfig.ConditionPathExists = alertFile;
              serviceConfig = {
                Type = "oneshot";
                ExecStart = notify;
              };
            };

            paths.pcr12-alert = {
              wantedBy = [ "graphical-session.target" ];
              pathConfig.PathChanged = alertFile;
            };
          };
        };

        custom = {
          persistence.directories = [ "/var/lib/pcr12" ];
          hardening.serviceExposure.pcr12-check = "1.1";
        };
      })
    ]
  );
}
