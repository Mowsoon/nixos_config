#!/bin/sh
export PATH=/run/current-system/sw/bin:$PATH
cd "$KERNEL_BUILD/kselftest/kselftest_install" || exit 1
set --
if [ -f "$KERNEL_BUILD/kselftest.args" ]; then
  set -- $(cat "$KERNEL_BUILD/kselftest.args")
fi
./run_kselftest.sh "$@" > "$KERNEL_BUILD/kselftest.log" 2>&1
{
  for state in freeze disk; do
    for level in freezer devices platform processors core; do
      echo "$level" > /sys/power/pm_test
      echo "$state" > /sys/power/state
      echo "$state $level: $?"
    done
  done
  echo none > /sys/power/pm_test
} > "$KERNEL_BUILD/pm-test.log" 2>&1
exit 0
