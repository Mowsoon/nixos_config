{ config, lib, ... }:
let
  cfg = config.custom.hardening;
in
{
  options.custom.hardening = {
    enable = lib.mkEnableOption "the kernel and privilege hardening baseline";
  };

  config = lib.mkIf cfg.enable {
    security = {
      apparmor.enable = true;
      audit.enable = true;
      auditd.enable = true;
      sudo.execWheelOnly = true;
    };

    nix.settings.allowed-users = [ "@wheel" ];

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
