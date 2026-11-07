swap=/dev/disk/by-id/virtio-hibernate-swap
step=$(tr ' ' '\n' < /proc/cmdline | sed -n 's/^hibernation_test=//p')

report() {
  echo "HIBERNATE-TEST $*" > /dev/console
}

attempt() {
  local name=$1 output
  shift
  if output=$("$@" 2>&1); then
    report "$name: allowed"
  else
    report "$name: refused, $(echo "$output" | head -n 1)"
  fi
}

swap_type() {
  blkid -o value -s TYPE "$swap" || echo none
}

describe() {
  report "kernel $(uname -r)"
  report "lockdown $(cat /sys/kernel/security/lockdown 2> /dev/null || echo unavailable)"
  report "power disk $(cat /sys/power/disk)"
  report "power state $(cat /sys/power/state)"
  report "swap signature $(swap_type)"
}

kernel_messages() {
  dmesg | grep -E 'PM: (Image|Cannot|Loading|hibernation: )|Lockdown|restricted PCR' | while read -r line; do
    report "dmesg $line"
  done || true
}

hibernate() {
  local token
  if [ "$(swap_type)" != swap ]; then
    mkswap "$swap" > /dev/null
  fi
  swapon "$swap"
  describe
  attempt "snapshot device" dd if=/dev/snapshot of=/dev/null count=0 status=none
  token=$(cat /proc/sys/kernel/random/uuid)
  report "token $token"
  echo shutdown > /sys/power/disk || report "hibernation mode not settable"
  if echo disk > /sys/power/state; then
    report "resumed with token $token"
  else
    report "hibernation refused"
    kernel_messages
  fi
}

check() {
  describe
  kernel_messages
}

ima_rule() {
  echo "measure func=FILE_CHECK pcr=$1" > /sys/kernel/security/ima/policy
}

pcr() {
  local zero
  zero=$(printf '%064d' 0)
  export TPM2TOOLS_TCTI=device:/dev/tpmrm0
  attempt "extend PCR 23" tpm2_pcrextend "23:sha256=$zero"
  attempt "reset PCR 23" tpm2_pcrreset 23
  attempt "extend PCR 16" tpm2_pcrextend "16:sha256=$zero"
  attempt "reset PCR 16" tpm2_pcrreset 16
  attempt "IMA rule measuring into PCR 23" ima_rule 23
  attempt "IMA rule measuring into PCR 16" ima_rule 16
}

case "$step" in
  hibernate) hibernate ;;
  check) check ;;
  pcr) pcr ;;
  *) report "unknown step '$step'" ;;
esac

report "done"
systemctl poweroff --no-block
