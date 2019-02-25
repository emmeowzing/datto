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
    if [ $# -lt 1 ]
    then
        printf "** ERROR: \`getIO\` expected >=1 argument, received %s\\n" \
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
            continue
        fi

        shift

        # Ensure this I/- satisfies all conditions.
        for f in "$@" "last_";
        do
            if [ "$f" == "last_" ]
            then
                break 2
            elif ! $f "$input"
            then
                break
            fi
        done
    done
    
    printf "%s" "$input"
}


##
# Condition on CPUs to pass to `getIO`.
# 
# TODO: check against CPUs already taken up by active VMs.
getCPUs()
{
    local cpu hostCPUs
    declare -i cpu hostCPUs
    
    cpu="$1"
    hostCPUs="$(nproc --ignore 2)"

    if [ "$cpu" -gt "$hostCPUs" ]
    then
        printf "**WARNING: number of available host CPUs is %s\\n" \
            "$hostCPUs" 1>&2
        if [[ "$(getIO "Proceed? [y|n]")" =~ ^[yY] ]]
        then
            printf "**WARNING: proceeding with %s CPUs\\n" "$cpu" 1>&2
        else
            return 1
        fi
    fi

    return 0
}


##
# 
getDisks()
{
    if ! [[ "$(getIO "Would you like to add disks now [y|n]")" =~ ^[Yy] ]]
    then
        return 1
    fi

    local disks previous
    declare -a disks

    disks=()
    previous=true   # Indicate whether we require an installer

    while true
    do
        disks+=("--disk")

        if [[ $previous && "$(getIO "Is this an installer? [y|n]")" =~ ^[Yy] ]]
        then
            
        fi
    done
}


##
# Set up the VM with variables.
setup()
{
    local name mem hostCPUs cpu disks ans installer previous
    declare -i mem hostCPUs cpu 
    declare -a disks

    # Save 2 processors for the host, at the very least.
    hostCPUs="$(nproc --ignore 2)"

    name="$(getIO "Provide the name")"
    mem="$(getIO "Provide the memory (in MiB)")"
    cpu="$(getIO "Provide the number of CPUs" getCPUs)"
    disks="$(getDisks)"

    disks[0]="${disks[0]} cdrom=$path,size=$size"

    printf "virt-install --name %s --memory %s --arch %s --vcpus %s --cpu host --security type=dynamic --clock=localtime " \
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
