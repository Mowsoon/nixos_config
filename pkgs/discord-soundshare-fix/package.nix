{
  lib,
  stdenv,
  fetchFromGitHub,
}:
stdenv.mkDerivation {
  pname = "discord-soundshare-fix";
  version = "0-unstable-2026-09-29";

  src = fetchFromGitHub {
    owner = "zxsleebu";
    repo = "discord-linux-soundshare-fix";
    rev = "1d30b18f50ae9ef67a9acf221639b5628c9d32a3";
    hash = "sha256-JkaVxzi1i+9yCvKicNmmh8+G2VvCAWpJDFFoAFPpSFw=";
  };

  patches = [ ./0001-preload-skip-restarts-only-while-Discord-shares-audi.patch ];

  buildPhase = ''
    runHook preBuild
    $CXX -std=c++20 -O2 -fPIC -shared -fvisibility=hidden -Wall -Wextra -Wpedantic \
      -Wl,-z,relro -Wl,-z,now native/preload.cc -ldl -o libdiscord_soundshare_fix_preload.so
    runHook postBuild
  '';

  doCheck = true;

  checkPhase = ''
    runHook preCheck
    $CXX -std=c++20 -O2 -fPIC -shared ${./tests/voice_module.cc} -o discord_voice.node
    $CXX -std=c++20 -O2 ${./tests/loader.cc} -ldl -o loader
    LD_PRELOAD=$PWD/libdiscord_soundshare_fix_preload.so ./loader $PWD/discord_voice.node
    runHook postCheck
  '';

  installPhase = ''
    runHook preInstall
    install -Dm444 -t $out/lib libdiscord_soundshare_fix_preload.so
    runHook postInstall
  '';

  meta = {
    description = "LD_PRELOAD hook that stops Discord from restarting its stream audio for every new playback stream";
    homepage = "https://github.com/zxsleebu/discord-linux-soundshare-fix";
    license = lib.licenses.mit;
    platforms = [ "x86_64-linux" ];
  };
}
