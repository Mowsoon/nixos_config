{ lib, pkgs, ... }:
let
  earlyMounts =
    lib.genAttrs
      [
        "/home"
        "/persist"
        "/var/log"
      ]
      (_: {
        neededForBoot = true;
      });
in
{
  imports = [
    ./disko.nix
    ./hardware.nix
    ./network.nix
    ../../modules/core/unfree.nix
    ../../modules/core/root-rollback.nix
    ../../modules/core/persistence.nix
    ../../modules/core/snapshots.nix
    ../../modules/security/secure-boot.nix
    ../../modules/security/luks.nix
    ../../modules/security/hardening.nix
  ];

  nixpkgs.hostPlatform = "x86_64-linux";

  networking.hostName = "hephaestus";

  nix.settings.experimental-features = [
    "nix-command"
    "flakes"
  ];

  boot.initrd.systemd.enable = true;

  custom = {
    secureBoot.enable = true;

    luks.tpm2Unlock = true;

    hardening.enable = true;

    rootRollback = {
      enable = true;
      device = "/dev/mapper/cryptroot";
    };

    persistence = {
      enable = true;
      root = "/persist";
    };

    snapshots = {
      enable = true;
      subvolumes = {
        home = "/home";
        persist = "/persist";
      };
    };
  };

  fileSystems = earlyMounts;

  services.btrfs.autoScrub = {
    enable = true;
    interval = "monthly";
    fileSystems = [ "/nix" ];
  };

  security.sudo.extraConfig = "Defaults lecture = never";

  zramSwap = {
    enable = true;
    algorithm = "zstd";
    memoryPercent = 50;
    priority = 100;
  };

  console.keyMap = "fr";
  time.timeZone = "Europe/Dublin";
  i18n.defaultLocale = "en_US.UTF-8";

  users = {
    mutableUsers = false;
    users.mowsoon = {
      isNormalUser = true;
      extraGroups = [ "wheel" ];
      hashedPasswordFile = "/persist/secrets/mowsoon.hash";
    };
  };

  virtualisation.vmVariantWithDisko = {
    disko = {
      tests.efi = true;
      imageBuilder = {
        copyNixStore = lib.mkForce true;
        pkgs = pkgs.extend (
          _: prev: {
            vmTools = prev.vmTools.override {
              kernelImage = prev.linux.target;
            };
          }
        );
      };
      devices.disk.main = {
        imageSize = "16G";
        content.partitions.luks.content.content.subvolumes."@swap".swap.swapfile.size = lib.mkForce "1G";
      };
    };
    custom = {
      nvidia.enable = lib.mkForce false;
      asus.enable = lib.mkForce false;
    };
    boot = {
      kernelParams = [
        "console=tty0"
        "console=ttyS0,115200n8"
      ];
      initrd.systemd.emergencyAccess = true;
      lanzaboote = {
        autoGenerateKeys.enable = true;
        autoEnrollKeys = {
          enable = true;
          autoReboot = true;
        };
      };
    };
    systemd = {
      services.generate-sb-keys.unitConfig.RequiresMountsFor = [ "/var/lib/sbctl" ];
      sleep.settings.Sleep.HibernateMode = "reboot";
    };
    users.users.mowsoon = {
      hashedPasswordFile = lib.mkForce null;
      hashedPassword = lib.fileContents ../vm-test/mowsoon.hash;
    };
    swapDevices = lib.mkForce [
      {
        device = "/swap/swapfile";
        priority = 0;
      }
    ];
    virtualisation = {
      tpm.enable = true;
      useBootLoader = true;
      useEFIBoot = true;
      bootPartition = null;
      efi.keepVariables = false;
      writableStore = false;
      sharedDirectories = lib.mkForce { };
      fileSystems = earlyMounts;
      memorySize = 4096;
      cores = 4;
      graphics = false;
    };
  };

  system.stateVersion = "26.11";
}
