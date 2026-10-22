{
  stdenv,
  kernel,
  kernelModuleMakeFlags,
}:
let
  subdir = "drivers/net/wireless/mediatek/mt76";
in
stdenv.mkDerivation {
  pname = "mt76";
  inherit (kernel) version src;

  unpackPhase = ''
    runHook preUnpack
    mkdir -p source/${subdir}
    cp -r $src/${subdir}/. source/${subdir}/
    chmod -R u+w source
    cd source
    runHook postUnpack
  '';

  patches = [ ./0001-wifi-mt76-mt7921-add-pci-restore-for-hibernate.patch ];

  nativeBuildInputs = kernel.moduleBuildDependencies;

  makeFlags = kernelModuleMakeFlags ++ [
    "-C"
    "${kernel.dev}/lib/modules/${kernel.modDirVersion}/build"
    "M=$(NIX_BUILD_TOP)/source/${subdir}"
    "INSTALL_MOD_PATH=${placeholder "out"}"
    "INSTALL_MOD_DIR=updates"
  ];

  buildFlags = [ "modules" ];

  installTargets = [ "modules_install" ];
}
