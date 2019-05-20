#!/bin/bash -xe

apt-get update
apt-get install -y ldap-auth-client nscd ldap-utils

auth-client-config -t nss -p lac_ldap

sed -i 's$^#bind_policy hard$bind_policy soft$' /etc/ldap.conf
sed -i 's$base dc=.*$base dc=mirantis,dc=net$' /etc/ldap.conf
sed -i 's$uri ldap.*$uri ldap://ldap-bud.bud.mirantis.net/$' /etc/ldap.conf
sed -i 's$^\(rootbinddn.*\)$#\1$' /etc/ldap.conf

cat << 'EOF' >> /etc/ldap/ldap.conf
BASE    dc=mirantis,dc=net
URI     ldap://ldap-bud.bud.mirantis.net/
EOF

cat << 'EOF' > /usr/share/pam-configs/my_mkhomedir
Name: activate mkhomedir
Default: yes
Priority: 900
Session-Type: Additional
Session:
        required                        pam_mkhomedir.so umask=0022 skel=/etc/skel
EOF

cat << 'EOF' >> /etc/security/group.conf
*;*;*;Al0000-2400;audio,cdrom,dialout,floppy,kvm,libvirtd
EOF

cat << 'EOF' > /usr/share/pam-configs/my_groups
Name: activate /etc/security/group.conf
Default: yes
Priority: 900
Auth-Type: Primary
Auth:
        required                        pam_group.so use_first_pass
EOF

cat << 'EOF' > /usr/local/sbin/ssh-ldap-keyauth
#!/bin/bash

/usr/bin/ldapsearch -x '(&(objectClass=posixAccount)(uid='"$1"'))' sshPublicKey | sed -n '/^ /{H;d};/sshPublicKey:/x;$g;s/\n *//g;s/sshPublicKey: //gp'
EOF

cat << 'EOF' >> /etc/ssh/sshd_config
AuthorizedKeysCommand /usr/local/sbin/ssh-ldap-keyauth
AuthorizedKeysCommandUser nobody
EOF

chmod +x /usr/local/sbin/ssh-ldap-keyauth
DEBIAN_FRONTEND=noninteractive pam-auth-update

#systemctl restart nscd.service;
#systemctl restart sshd.service;
