#! /bin/bash
# Make the process of deploying Windows virtualizations easier with 
# libvirt/qemu-kvm. This isn't a perfect script, but as long as you enter the
# proper information, it'll make your life a lot easier than sifting through
# the manpage.
#
# A few notes about the default configuration offered here:
#
# --cpu host -- offers the best performance, but may cause problems if you ever
#               migrate a VM from the environment it was created on. Modify
#               this to `host-model-only` for a tradeoff between portability
#               and performance.


##
# If all required packages aren't installed, install them.
checkInstalled()
{
    if ! dpkg -s virtinst qemu-kvm libvirt-daemon-system libvirt-clients \
        bridge-utils virt-viewer &>/dev/null
    then
        if [[ "$(getIO "install [y|n]")" =~ ^[^yY] ]]
        then
            printf "** ERROR: prerequisites not satisfied\\n" 1>&2
            exit 1
        fi

        apt update -y
        apt install virtinst qemu-kvm libvirt-daemon-system libvirt-clients \
            bridge-utils virt-viewer -y
    fi

    printf "All prerequisites satisfied.\\n"
}


##
# Get valid user input for various things.
getIO()
{
    if [ $# -ge 1 ]
    then
        printf "** ERROR: \`getIO\` expected 1 argument, received %s\\n" \
            "$#" 1>&2
        exit 1
    fi

    local input f
    
    while true
    do
        read -r -p "$1: " input

        # Ensure the I/- isn't a null string.
        if ! [ "$input" ]
        then
            printf "** ERROR: must enter non-empty string\\n" 1>&2
        fi

        shift

        # Ensure this I/- satisfies all conditions.
        for f in $# "last_";
        do
            if [ "$f" == "last_" ]
            then
                break 2
            elif ! [ "$($f "$input")" ]
            then
                break
            fi
        done
    done
    
    printf "%s" "$input"
}


##
# Condition on CPUs to pass to `getIO`.
getCPUs()
{
    local cpu
    declare -i cpu

    
}


##
# Set up the VM with variables.
setup()
{
    local name mem hostCPUs cpu disks ans installer
    declare -i mem hostCPUs cpu 
    declare -a disks

    # Save 2 processors for the host, at the very least.
    hostCPUs="$(nproc --ignore 2)"

    name="$(getIO "Provide the name")"
    mem="$(getIO "Provide the memory (in MiB)")"

    # TODO: check against CPUs already taken up by active VMs.
    # Wrapping `getIO` here because of the additional complexity.
    while true
    do
        cpu="$(getIO "Provide the number of CPUs")"
        if [ "$cpu" -gt "$hostCPUs" ]
        then
            printf "**WARNING: number of available host CPUs is %s\\n" \
                "$hostCPUs" 1>&2
            if [[ "$(getIO "proceed? [y|n]")" =~ ^[yY] ]]
            then
                printf "**WARNING: proceeding with %s CPUs\\n" "$cpu" 1>&2
                break
            fi
        fi
        break
    done

    # Add disks.
    disks=()
    previous=false

    read -r -p "Would you like to add disks now [y|n]: " ans
    
    if [[ "$ans" =~ ^[Yy] ]]
    then
        # Loop until we're done adding disks.
        while true
        do
            disks+=("--disk")

            # Set up the installer disk/ISO/img.
            if ! [ $previous ]
            then
                read -r -p "Is this an installer? [y|n]" installer

                if [ "$installer" ]
                then
                    # Get a valid installer.
                    while true
                    do
                        read -r -p "Enter a valid file path: " path
                        pathM="${path##*.}"

                        if ! [ -e "$path" ]
                        then
                            printf "**ERROR: enter a valid path, received %s\\n" \
                                "$path"
                        elif [ "$pathM" != "iso" ] || [ "$pathM" != "img" ]
                        then
                            read -r -p "Extension is $pathM, continue [y|n]"
                        else
                            break
                        fi
                    done

                    size="$(getIO "size of installer disk")"

                    # Update disks array, putting this cdrom first ofc.
                    disks[0]="${disks[0]} cdrom=$path,size=$size"
                fi
                previous=true
            fi

            # Handle adding arbitrary disks.
            while true
            do
                size="$(getIO "the size (GiB)")"
            done

            #disks[
        done
    fi

    printf "virt-install --name %s --memory %s --arch %s --vcpus %s --cpu host
        --security type=dynamic --clock=localtime " \
        "$name" "$mem" "$(uname -m)" "$cpu"
}


main()
{
    local runnable input

    # Ensure prerequisites are satisfied.
    checkInstalled

    # Set up the VM.
    runnable="$(setup)"

    printf "\033[1mString:\033[0m \033[32;1m%s\033[0m\\n" "$runnable"

    read -r -p "Would you like to execute this string as a dry run [y|n]: " input
    if [[ "$input" =~ ^[Yy] ]]
    then
        eval "$runnable \-\-dry-run"
    fi

    # Unset all the variables/function declarations.
    unset -f checkInstalled
    unset -f getIO
    unset -f setup
}


main
unset -f main
