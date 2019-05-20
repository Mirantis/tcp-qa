#!/bin/bash -xe

apt-get -y remove --purge unattended-upgrades || true
apt-get -y autoremove --purge
apt-get -y clean

rm -rf /var/lib/apt/lists/* || true
rm -rv /etc/apt/sources.list.d/* || true
rm -rv /etc/apt/preferences.d/* || true
echo > /etc/apt/sources.list  || true
rm -vf /usr/sbin/policy-rc.d || true

echo "cleaning up hostname"
sed -i "/.*ubuntu.*/d" /etc/hosts
sed -i "/.*salt.*/d" /etc/hosts

echo "cleaning up guest additions"
rm -rf VBoxGuestAdditions_*.iso VBoxGuestAdditions_*.iso.? || true

echo "cleaning up dhcp leases"
rm -rf /var/lib/dhcp/* || true
rm -rfv /var/lib/ntp/ntp.conf.dhcp || true

echo "cleaning up udev rules"
rm -fv /etc/udev/rules.d/70-persistent-net.rules || true
rm -rf /dev/.udev/ || true
rm -fv /lib/udev/rules.d/75-persistent-net-generator.rules || true

echo "cleaning up minion_id for salt"
rm -vf /etc/salt/minion_id || true

echo "cleaning up resolvconf"
sed -i '/172\.18\.208\.44/d' /etc/resolvconf/resolv.conf.d/base

echo "cleaning up /var/cache/{apt,salt}/*"
rm -rf /var/cache/{apt,salt}/* || true

rm -rf /root/.cache || true
rm -rf /root/.ssh/known_hosts || true

# Remove flags
rm -v /done_ubuntu_base || true
rm -v /done_ubuntu_salt_bootstrap || true

# Force cleanup cloud-init data, if it was
if [[ -d '/var/lib/cloud/' ]] ; then
  rm -rf /var/lib/cloud/* || true
  cloud-init clean || true
  echo > /var/log/cloud-init-output.log || true
  echo > /var/log/cloud-init.log || true
fi

cat << EOF > /etc/network/interfaces
# This file describes the network interfaces available on your system
# and how to activate them. For more information, see interfaces(5).

# The loopback network interface
auto lo
iface lo inet loopback

# Source interfaces
# Please check /etc/network/interfaces.d before changing this file
# as interfaces may have been defined in /etc/network/interfaces.d
# See LP: #1262951
source /etc/network/interfaces.d/*.cfg
EOF

# Clear\drop cache's
sync
echo 3 > /proc/sys/vm/drop_caches
