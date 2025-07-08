#!/bin/bash


set -euo pipefail


CRYPTED_DEVICE_NAME=hdd_crypt
VG_NAME=hdd
DEVICE=/dev/sdb1

#parted /dev/sdb mklabel gpt
#parted /dev/sdb mkpart primary 0% 100%

cryptsetup luksFormat $DEVICE

echo "Create keys"
dd if=/dev/urandom of=/root/$CRYPTED_DEVICE_NAME.key bs=1024 count=4
chmod 400 /root/*.key

echo "Add keys to luks"
cryptsetup luksAddKey "$DEVICE" /root/$CRYPTED_DEVICE_NAME.key

echo "Setup crypttab"
cat >> /etc/crypttab <<EOF
$CRYPTED_DEVICE_NAME UUID=$(blkid -s UUID -o value $DEVICE) /root/$CRYPTED_DEVICE_NAME.key luks
EOF

cryptsetup open $DEVICE $CRYPTED_DEVICE_NAME --key-file /root/$CRYPTED_DEVICE_NAME.key

pvcreate /dev/mapper/$CRYPTED_DEVICE_NAME
vgcreate $VG_NAME /dev/mapper/$CRYPTED_DEVICE_NAME
lvcreate -L 4G $VG_NAME -n log
lvcreate -l 100%FREE $VG_NAME -n data
mkfs.ext4 /dev/$VG_NAME/data
mkfs.ext4 /dev/$VG_NAME/log

mkdir -p /data
mkdir -p /log

cat >> /etc/fstab <<EOF
/dev/$VG_NAME/data /data ext4 defaults 0 2
EOF

systemctl daemon-reload

mount -a

