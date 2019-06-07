#! /bin/bash
# Download and save configuration files from pfSense and snapshot with ZFS.

IPs=( "192.168.1.90" )
login="*"
password="*"
PATH="/homePool/home/VMs/pfSenseBackups"

if ! [ -z "$(/bin/ls -A /homePool/home/VMs/pfSenseBackups)" ]
then
    /bin/rm /homePool/home/VMs/pfSenseBackups/*
fi


for IP in "${IPs[@]}"
do
    /usr/bin/wget -qO- --keep-session-cookies --save-cookies "$PATH/cookies.txt" --no-check-certificate "http://$IP/diag_backup.php" \
        | /bin/grep "name='__csrf_magic'" | /bin/sed 's/.*value="\(.*\)".*/\1/' > "$PATH/csrf.txt"

    /usr/bin/wget -qO- --keep-session-cookies --load-cookies "$PATH/cookies.txt" --save-cookies cookies.txt --no-check-certificate \
        --post-data "login=Login&usernamefld=$login&passwordfld=$password&__csrf_magic=$(/bin/cat "$PATH/csrf.txt")" \
        "http://$IP/diag_backup.php" | /bin/grep "name='__csrf_magic'" | /bin/sed 's/.*value="\(.*\)".*/\1/' > "$PATH/csrf2.txt"

    /usr/bin/wget --keep-session-cookies --load-cookies cookies.txt --no-check-certificate \
        --post-data "download=download&donotbackuprrd=yes&__csrf_magic=$(/usr/bin/head -n 1 "$PATH/csrf2.txt")" \
        "http://$IP/diag_backup.php" -O "$PATH/config-router-$IP-$(/bin/date +%Y%m%d%H%M%S).xml"
done


if ! [ -z "$(/bin/ls -A /homePool/home/VMs/pfSenseBackups/*.txt)" ]
then
    /bin/rm /homePool/home/VMs/pfSenseBackups/*.txt
fi

/sbin/zfs snapshot "homePool/home/VMs/pfSenseBackups@$(/bin/date +%s)"
