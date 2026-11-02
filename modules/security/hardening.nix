{ config, lib, ... }:
let
  cfg = config.custom.hardening;
in
{
  options.custom.hardening = {
    enable = lib.mkEnableOption "the kernel and privilege hardening baseline";

    serviceExposure = lib.mkOption {
      type = lib.types.attrsOf (lib.types.strMatching "[0-9]+\\.[0-9]");
      default = { };
      example = {
        chronyd = "3.3";
      };
      description = "Highest exposure score, as computed by `systemd-analyze security`, accepted for each system service; set by the module that owns the service.";
    };
  };

  config = lib.mkIf cfg.enable {
    security = {
      apparmor.enable = true;
      audit.enable = true;
      auditd.enable = true;
      sudo.execWheelOnly = true;
    };

    nix.settings.allowed-users = [ "@wheel" ];

    custom.hardening.serviceExposure.nscd = "8.2";

    boot.kernel.sysctl = {
      "kernel.kptr_restrict" = 2;
      "kernel.dmesg_restrict" = 1;
      "kernel.unprivileged_bpf_disabled" = 1;
      "net.core.bpf_jit_harden" = 2;
      "kernel.kexec_load_disabled" = 1;
      "dev.tty.ldisc_autoload" = 0;
    };
  };
}
