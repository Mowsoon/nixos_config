{
  runCommand,
  bpftools,
  kernel,
}:
runCommand "vmlinux-h-${kernel.version}" { nativeBuildInputs = [ bpftools ]; } ''
  mkdir -p $out/include
  bpftool btf dump file ${kernel.dev}/vmlinux format c > $out/include/vmlinux.h
''
