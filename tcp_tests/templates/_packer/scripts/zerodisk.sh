#!/bin/bash
set -x

dd if=/dev/zero of=/EMPTY bs=1M || true
rm -f /EMPTY

sync
echo 3 > /proc/sys/vm/drop_caches
