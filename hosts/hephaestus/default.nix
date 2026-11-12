{ inputs, lib, ... }:
let
  hardwareIds = import "${inputs.nixos-private}/hosts/hephaestus/hardware-ids.nix";
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
    ../../modules/core/fhs-compat.nix
    ../../modules/virtualisation/docker.nix
    ../../modules/desktop/boot-splash.nix
    ../../modules/desktop/claude-desktop.nix
    ../../modules/desktop/firefox.nix
    ../../modules/desktop/plasma.nix
    ../../modules/desktop/rgb-effects.nix
    ../../modules/desktop/theme.nix
    ../../modules/security/secure-boot.nix
    ../../modules/security/luks.nix
    ../../modules/security/lockdown.nix
    ../../modules/security/pcrlock.nix
    ../../modules/security/hardening.nix
    ../../modules/security/supply-chain.nix
  ];

  nixpkgs.hostPlatform = "x86_64-linux";

  networking.hostName = "hephaestus";

  nix.settings.experimental-features = [
    "nix-command"
    "flakes"
  ];

  boot.loader.timeout = 1;

  custom = {
    secureBoot = {
      enable = true;
      sealedKeys = true;
    };

    luks = {
      tpm2Unlock = true;
      measureVolumeKey = true;
    };

    lockdown = {
      moduleCertificates = true;
      mode = "integrity";
    };

    pcrlock = {
      enable = true;
      pcrs = [
        0
        2
        5
        8
        11
        13
        14
      ];
      lockCredentials = true;
    };

    hardening.enable = true;

    supplyChain.enable = true;

    docker.enable = true;

    claudeDesktop.enable = true;

    plasma.enable = true;

    theme.enable = true;

    bootSplash.enable = true;

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

    fhsCompat.enable = true;

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

  fileSystems = import ./early-mounts.nix lib;

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
    imports = [ ./vm.nix ];
    disko.devices.disk.main.imageSize = "32G";
    custom = {
      nvidia.enable = lib.mkForce false;
      asus.enable = lib.mkForce false;
      windowsVolume = {
        device = lib.mkForce "/dev/disk/by-id/virtio-windows-test";
        type = "luks";
        diskSerial = lib.mkForce "windows-test";
      };
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
