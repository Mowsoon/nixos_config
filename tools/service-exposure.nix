{
  lib,
  runCommand,
  bubblewrap,
  systemd,
  units,
  thresholds,
}:
runCommand "service-exposure"
  {
    nativeBuildInputs = [
      bubblewrap
      systemd
    ];
  }
  (
    lib.concatStrings (
      lib.mapAttrsToList (service: threshold: ''
        if ! bwrap --ro-bind /nix /nix --tmpfs /run --tmpfs /etc --tmpfs /usr --tmpfs /var --tmpfs /tmp --proc /proc --dev /dev \
            systemd-analyze security --offline=yes --threshold=${
              toString (lib.toIntBase10 (lib.replaceStrings [ "." ] [ "" ] threshold))
            } --no-pager ${units}/${service}.service > report 2>&1; then
          tail -n 2 report
          echo "${service}.service is above its threshold ${threshold}"
          exit 1
        fi
        echo "${service}.service: $(grep -o 'exposure level for .*' report)"
      '') thresholds
    )
    + ''
      touch $out
    ''
  )
