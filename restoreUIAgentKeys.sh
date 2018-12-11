#! /bin/bash
# Quick and dirty script that restores keys from
# `/home/configBackup/.zfs/snapshot/*/files/datto/config/keys/` to
# `/datto/config/keys/` if they exist for a particular agent.
#
# Brandon Doyle. Last updated Dec. 11, 2018.


##
# Get an agent's name to search the configBackup subdirectory snapshots for.
getAgentName()
{
    local agentName

    while true
    do
        read -rp "Enter UUID: " agentName
        
        # Validation; basically ensure they entered _something_ - in this script's
        # case, it's pretty simple.
        if ! [ "$agentName" ]
        then
            printf "\\n\\t\\033[31;1mERROR: please enter a UUID\\033[0m\\n\\n" 1>&2
            continue
        fi

        break
    done

    printf "%s" "$agentName"

    return 0
}


##
# Search snapshots for this set of keys and present the user with it.
searchConfigBackup()
{
    if [ $# != 1 ]
    then
        printf "\\n\\t\\033[31;1m** ERROR: \`searchConfigBackup\` expected 1 argument, received %s\\033[0m\\n\\n" "$#" 1>&2
        return 1
    fi

    local uuid="$1"
    local findings snapshot snapshots length i file

    snapshots=(/home/configBackup/.zfs/snapshot/*)
    length=$(( ${#snapshots[@]} - 1 ))

    # Iterate over snapshots from most recent to earliest, looking for the most
    # recent set of keys.
    for i in $(seq "$length" -1 0)
    do
        snapshot="${snapshots[$i]}"

        printf "%s\\n" "$snapshot"
        printf "Current Snapshot: %s\\n" "$(date -d "@${snapshot##*/}")"
        findings=( $(find "$snapshot/files/datto/config/keys/" -name "*$uuid*") )

        # If there are keys here, then ask user if they wish to restore them.
        if [ "${#findings[@]}" -gt "1" ]
        then
            printf "\\n\\t\\033[32;1mI found something! YAY!\\033[0m\\n"
            printf "\\t\\033[32;1mWould you like to restore these item(s)?\\033[0m\\n\\n"

            printf "\\t\\033[32m%s\\033[0m\\n" "${findings[@]##*/}"
            printf "\\n"

            while true
            do
                read -rp "Restore [Yy|n]: " decision

                if [[ "$decision" =~ ^[Yy] ]]
                then
                    printf "\\nRestoring keys.\\n\\n"
        
                    # Restore files to keys subdir.
                    for file in "${findings[@]}"
                    do
                        cp "$file" "/datto/config/keys"
                    done

                    printf "Keys restored to /datto/config/keys.\\n\\n"
        
                    return 0
                else
                    printf "\\n\\t\\033[31;1mINFO: Very well; skipping current set and searching for a former set.\\033[0m\\n\\n"
                    break
                fi
            done
        fi
    done

    printf "\\033[31;1mNo keys restored.\\033[0m\\n"

    return 0
}


date
name="$(getAgentName)"
searchConfigBackup "$name"


unset -f name
unset -f searchConfigBackup
