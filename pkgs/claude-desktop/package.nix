{
  lib,
  stdenv,
  fetchurl,
  dpkg,
  autoPatchelfHook,
  makeWrapper,
  alsa-lib,
  at-spi2-core,
  bubblewrap,
  cairo,
  cups,
  dbus,
  expat,
  glib,
  gtk3,
  libappindicator-gtk3,
  libcap_ng,
  libdrm,
  libgbm,
  libGL,
  libnotify,
  libseccomp,
  libsecret,
  libx11,
  libxcb,
  libxcomposite,
  libxdamage,
  libxext,
  libxfixes,
  libxkbcommon,
  libxrandr,
  libxtst,
  nspr,
  nss,
  pango,
  pipewire,
  qemu_kvm,
  socat,
  systemd,
  util-linux,
  virtiofsd,
  xdg-utils,
}:
stdenv.mkDerivation (finalAttrs: {
  pname = "claude-desktop";
  version = "2.26454.2";

  src = fetchurl {
    url = "https://downloads.claude.ai/claude-desktop/apt/stable/pool/main/c/claude-desktop/claude-desktop_${finalAttrs.version}_amd64.deb";
    sha256 = "b251a0224a8635874f33598df8ed8952b427f84815ee59580cc022d6bdb2430f";
  };

  nativeBuildInputs = [
    dpkg
    autoPatchelfHook
    makeWrapper
  ];

  buildInputs = [
    alsa-lib
    at-spi2-core
    cairo
    cups
    dbus
    expat
    glib
    gtk3
    libcap_ng
    libdrm
    libgbm
    libnotify
    libseccomp
    libsecret
    libx11
    libxcb
    libxcomposite
    libxdamage
    libxext
    libxfixes
    libxkbcommon
    libxrandr
    libxtst
    nspr
    nss
    pango
    pipewire
    stdenv.cc.cc.lib
    systemd
    util-linux
  ];

  runtimeDependencies = [
    libGL
    libappindicator-gtk3
    libnotify
    libsecret
    (lib.getLib systemd)
  ];

  unpackPhase = ''
    runHook preUnpack
    dpkg-deb --fsys-tarfile "$src" | tar --extract --no-same-owner --no-same-permissions
    runHook postUnpack
  '';

  installPhase = ''
    runHook preInstall

    mkdir -p $out
    cp -r usr/lib usr/share $out/
    rm -rf $out/share/lintian $out/share/doc
    chmod 0755 $out/lib/claude-desktop/chrome-sandbox
    test -x $out/lib/claude-desktop/claude-desktop

    makeWrapper $out/lib/claude-desktop/claude-desktop $out/bin/claude-desktop \
      --prefix PATH : ${
        lib.makeBinPath [
          bubblewrap
          qemu_kvm
          socat
          virtiofsd
          xdg-utils
        ]
      } \
      --add-flags "\''${NIXOS_OZONE_WL:+\''${WAYLAND_DISPLAY:+--ozone-platform-hint=auto --enable-features=WaylandWindowDecorations --enable-wayland-ime=true}}"

    for desktopFile in $out/share/applications/*.desktop; do
      substituteInPlace "$desktopFile" --replace-quiet /usr/bin/claude-desktop claude-desktop
    done

    runHook postInstall
  '';

  meta = {
    description = "Official Claude desktop application repackaged from the Debian archive";
    homepage = "https://claude.com/download";
    license = lib.licenses.unfree;
    sourceProvenance = [ lib.sourceTypes.binaryNativeCode ];
    platforms = [ "x86_64-linux" ];
    mainProgram = "claude-desktop";
  };
})
