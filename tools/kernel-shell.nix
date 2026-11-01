{
  mkShell,
  linuxPackages_zen,
  b4,
  bpftools,
  clang,
  gitFull,
  llvm,
  ncurses,
  pahole,
  pkg-config,
  qemu_kvm,
}:
mkShell {
  inputsFrom = [ linuxPackages_zen.kernel ];
  packages = [
    b4
    bpftools
    clang
    gitFull
    llvm
    ncurses
    pahole
    pkg-config
    qemu_kvm
  ];
  hardeningDisable = [ "all" ];
  KERNEL_BASE_CONFIG = linuxPackages_zen.kernel.configfile;
}
