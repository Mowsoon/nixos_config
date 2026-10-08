{
  config,
  lib,
  utils,
  ...
}:
let
  cfg = config.custom.rootRollback;
  deviceUnit = "${utils.escapeSystemdPath cfg.device}.device";
in
{
  options.custom.rootRollback = {
    enable = lib.mkEnableOption "the rollback of the Btrfs root subvolume to an empty one on every cold boot";

    device = lib.mkOption {
      type = lib.types.str;
      example = "/dev/mapper/cryptroot";
      description = "Unlocked block device that holds the Btrfs filesystem.";
    };

    subvolume = lib.mkOption {
      type = lib.types.str;
      default = "@root";
      description = "Name of the subvolume mounted on `/`, relative to the top of the filesystem.";
    };

    retentionDays = lib.mkOption {
      type = lib.types.ints.positive;
      default = 30;
      description = "Number of days a previous root is kept under `old_roots` before deletion.";
    };
  };

  config = lib.mkIf cfg.enable {
    boot.initrd.systemd.services.rollback-root = {
      description = "Roll back the Btrfs root subvolume";
      wantedBy = [ "initrd.target" ];
      requires = [ deviceUnit ];
      after = [
        deviceUnit
        "systemd-hibernate-resume.service"
      ];
      before = [ "sysroot.mount" ];
      unitConfig.DefaultDependencies = false;
      serviceConfig.Type = "oneshot";
      script = ''
        top=/run/rollback-root
        root="$top/${cfg.subvolume}"
        staging="$top/${cfg.subvolume}.new"
        archive="$top/old_roots"
        cutoff=$(( $(date +%s) - ${toString cfg.retentionDays} * 86400 ))

        delete_subvolume() {
          local child
          while IFS= read -r child; do
            delete_subvolume "$top/$child"
          done < <(btrfs subvolume list -o "$1" | cut -d ' ' -f 9-)
          btrfs subvolume delete "$1"
        }

        mkdir -p "$top"
        mount -o subvolid=5 ${cfg.device} "$top"
        mkdir -p "$archive"

        if [[ -e "$staging" ]]; then
          delete_subvolume "$staging"
        fi
        btrfs subvolume create "$staging"

        if [[ -e "$root" ]]; then
          stamp=$(date --date="@$(stat -c %Y "$root")" +%Y-%m-%d_%H-%M-%S)
          mv -T "$root" "$archive/$stamp"
        fi
        mv -T "$staging" "$root"

        for old in "$archive"/*; do
          if [[ -d "$old" ]] && (( $(stat -c %Y "$old") < cutoff )); then
            delete_subvolume "$old"
          fi
        done

        umount "$top"
      '';
    };
  };
}
