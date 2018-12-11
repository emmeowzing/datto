#! /bin/bash

# Get the file name from the user
printf "$(tput setaf 6)Please enter the file name from the directory /datto/array1/.recv:\n > $(tput setaf 7)"
read ROOTFILENAME

#Sanitize ".." from filename to prevent CD abuse and remove potentially dangerous characters
ROOTFILENAME=$(echo $ROOTFILENAME | sed -e 's/\.\.//g' | tr -d '[|& <>;$^%~\\[]"`(){}+=]')

# Check to see if the file exists in the recv folder
# If it does not, exit
if [ ! -e "/datto/array1/.recv/$ROOTFILENAME" ]; then
    printf "$(tput setaf 1)File name is incorrect, exiting...\n\n$(tput setaf 7)"
    unset ROOTFILENAME
    exit 1
fi

# Set deviceID from the format of the send file name.
# awk reads in reverse because there is the potential for an agent name to have a hyphen in it.
# This would create problems with the hyphen delimiter if reading from beginning to end
ROOTDEVID=$(ls /datto/array1/.recv/$ROOTFILENAME | awk -F "[.-]" '{print $(NF-5)}')
ROOTSECRETKEY=$(grep $ROOTDEVID /etc/passwd | awk -F "[/:]" '{print $1}')

# Get confirmation of the change from the user
printf "\n$(tput setaf 6)This will change the ownership of file $(tput setaf 5)$ROOTFILENAME$(tput setaf 6) to secret key $(tput setaf 5)$ROOTSECRETKEY$(tput setaf 6) for devID $(tput setaf 5)$ROOTDEVID$(tput setaf 6).  \nIs this correct? $(tput setaf 1)Y/N: $(tput setaf 7)"
read CHOWNCONFIRM
printf "\n"

# Confirm they have verified they want to make the change
# If yes, chown the appropriate file to the secretKey, unset variables and exit cleanly
# If no, unset variables and exit
if  [ "$CHOWNCONFIRM" == "Y" ] || [ "$CHOWNCONFIRM" == "y" ]; then
    chown $ROOTSECRETKEY:www-data /datto/array1/.recv/$ROOTFILENAME
    printf "Change complete.  $(tput setaf 2)$ROOTFILENAME $(tput setaf 7)is now owned by secret key $(tput setaf 2)$ROOTSECRETKEY $(tput setaf 7)for devID $(tput setaf 2)$ROOTDEVID\n$(tput setaf 7)\n"
    ls -lash /datto/array1/.recv/$ROOTFILENAME
    printf "\n"
    unset ROOTDEVID
    unset ROOTFILENAME
    unset ROOTSECRETKEY
    unset CHOWNCONFIRM
    exit 0
else
    printf "$(tput setaf 1)Script terminated.  No changes made.\n\n$(tput setaf 7)"
    unset ROOTDEVID
    unset ROOTFILENAME
    unset ROOTSECRETKEY
    unset CHOWNCONFIRM
    exit 1
fi