{
  lib,
  mkShell,
  writeShellScriptBin,
  linuxPackages_zen,
  b4,
  bpftools,
  clang,
  gitFull,
  lld,
  llvm,
  ncurses,
  pahole,
  pkg-config,
  qemu_kvm,
}:
let
  clangBpf = writeShellScriptBin "clang-bpf" ''
    exec ${lib.getExe clang} -Wno-unused-command-line-argument "$@"
  '';
in
mkShell {
  inputsFrom = [ linuxPackages_zen.kernel ];
  packages = [
    b4
    bpftools
    clang
    gitFull
    lld
    llvm
    ncurses
    pahole
    pkg-config
    qemu_kvm
  ];
  hardeningDisable = [ "all" ];
  KERNEL_BASE_CONFIG = linuxPackages_zen.kernel.configfile;
  CLANG = lib.getExe clangBpf;
}
