#!/bin/bash

set -e

# Some env must be defined
[[ -z "${DB_INSTANCE}" ]] && echo 'Environment DB_INSTANCE is empty' 1>&2 && exit 1
[[ -z "${CEGA_ENDPOINT}" ]] && echo 'Environment CEGA_ENDPOINT is empty' 1>&2 && exit 1
[[ -z "${CEGA_ENDPOINT_CREDS}" ]] && echo 'Environment CEGA_ENDPOINT_CREDS is empty' 1>&2 && exit 1
[[ -z "${CEGA_ENDPOINT_JSON_PASSWD}" ]] && echo 'Environment CEGA_ENDPOINT_JSON_PASSWD is empty' 1>&2 && exit 1
[[ -z "${CEGA_ENDPOINT_JSON_PUBKEY}" ]] && echo 'Environment CEGA_ENDPOINT_JSON_PUBKEY is empty' 1>&2 && exit 1

EGA_DB_IP=$(getent hosts ${DB_INSTANCE} | awk '{ print $1 }')
EGA_UID=$(id -u lega)
EGA_GID=$(id -g lega)

# For the home directories
mkdir -p /lega
chmod 750 /lega

cat > /etc/ega/auth.conf <<EOF
enable_cega = yes
cega_endpoint = ${CEGA_ENDPOINT}
cega_creds = ${CEGA_ENDPOINT_CREDS}
cega_json_passwd = ${CEGA_ENDPOINT_JSON_PASSWD}
cega_json_pubkey = ${CEGA_ENDPOINT_JSON_PUBKEY}

##################
# NSS & PAM
##################
# prompt = Knock Knock:
ega_uid = ${EGA_UID}
ega_gid = ${EGA_GID}
# ega_gecos = EGA User
# ega_shell = /sbin/nologin

ega_dir = /lega
ega_dir_attrs = 2750 # rwxr-s---

##################
# FUSE mount
##################
ega_fuse_exec = /usr/bin/ega-inbox
ega_fuse_flags = nodev,noexec,suid,default_permissions,allow_other,uid=${EGA_UID},gid=${EGA_GID}
EOF

cp /temp/conf.ini /etc/ega/conf.ini

# for the ramfs cache
mkdir -p /ega/cache
sed -i -e '/ega/ d' /etc/fstab
echo "ramfs /ega/cache ramfs   size=200m 0 0" >> /etc/fstab
mount /ega/cache

# Changing permissions
echo "Changing permissions for /ega/inbox"
chown lega:lega /ega/inbox
chmod 750 /ega/inbox
chmod g+s /ega/inbox # setgid bit

# Start cronie
echo "Starting cron"
cat > /usr/local/bin/fuse_cleanup.sh <<EOF
#!/bin/bash

set -e

for mnt in \$1/*
do
    { umount \${mnt} &>/dev/null && rmdir \${mnt}; } || :
done
EOF
chmod 750 /usr/local/bin/fuse_cleanup.sh

cat > /etc/crontab <<EOF
# Example of job definition:
# .---------------- minute (0 - 59)
# |  .------------- hour (0 - 23)
# |  |  .---------- day of month (1 - 31)
# |  |  |  .------- month (1 - 12) OR jan,feb,mar,apr ...
# |  |  |  |  .---- day of week (0 - 6) (Sunday=0 or 7) OR sun,mon,tue,wed,thu,fri,sat
# |  |  |  |  |
# *  *  *  *  * user-name  command to be executed

*/5 * * * * root /usr/local/bin/fuse_cleanup.sh /lega
EOF
crond -s

echo "Starting the SFTP server"
exec /usr/sbin/ega -D -e -f /etc/ega/sshd_config