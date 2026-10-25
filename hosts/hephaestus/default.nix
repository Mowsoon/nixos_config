{
  inputs,
  lib,
  pkgs,
  ...
}:
let
  hardwareIds = import "${inputs.nixos-private}/hosts/hephaestus/hardware-ids.nix";
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
    ./home.nix
    ./opensnitch.nix
    ../../modules/core/unfree.nix
    ../../modules/core/root-rollback.nix
    ../../modules/core/persistence.nix
    ../../modules/core/snapshots.nix
    ../../modules/core/windows-volume.nix
    ../../modules/core/nix-maintenance.nix
    ../../modules/core/memory.nix
    ../../modules/virtualisation/docker.nix
    ../../modules/desktop/claude-desktop.nix
    ../../modules/desktop/firefox.nix
    ../../modules/desktop/plasma.nix
    ../../modules/desktop/rgb-effects.nix
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

  boot = {
    initrd.systemd.enable = true;
    loader.timeout = 1;
  };

  custom = {
    secureBoot.enable = true;

    luks.tpm2Unlock = true;

    hardening.enable = true;

    docker.enable = true;

    claudeDesktop.enable = true;

    plasma.enable = true;

    firefox.enable = true;

    rgbEffects = {
      enable = true;
      keys.enable = true;
      audio.enable = true;
      sleepPolicy.enable = true;
      notifications.enable = true;
      screen.enable = true;
    };

    nixMaintenance.enable = true;

    memory.enable = true;

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

    windowsVolume = {
      enable = true;
      device = "/dev/disk/by-partuuid/${hardwareIds.windowsPartuuid}";
      diskSerial = hardwareIds.windowsDiskSerial;
    };
  };

  fileSystems = earlyMounts;

  services.btrfs.autoScrub = {
    enable = true;
    interval = "monthly";
    fileSystems = [ "/nix" ];
  };

  security.sudo.extraConfig = "Defaults lecture = never";

  console.keyMap = "fr";
  time.timeZone = "Europe/Dublin";
  i18n = {
    defaultLocale = "en_US.UTF-8";
    extraLocaleSettings = {
      LC_TIME = "en_IE.UTF-8";
      LC_PAPER = "en_IE.UTF-8";
      LC_MEASUREMENT = "en_IE.UTF-8";
    };
  };

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
        imageSize = "32G";
        content.partitions.luks.content.content.subvolumes."@swap".swap.swapfile.size = lib.mkForce "1G";
      };
    };
    custom = {
      nvidia.enable = lib.mkForce false;
      asus.enable = lib.mkForce false;
      windowsVolume = {
        device = lib.mkForce "/dev/disk/by-id/virtio-windows-test";
        type = "luks";
        diskSerial = lib.mkForce "windows-test";
      };
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
      emptyDiskImages = [
        {
          size = 512;
          driveConfig.deviceExtraOpts.serial = "windows-test";
        }
      ];
      memorySize = 8192;
      cores = 4;
      graphics = true;
      qemu.options = [ "-cpu host" ];
    };
  };

  system.stateVersion = "26.11";
}
