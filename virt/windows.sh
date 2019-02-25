#! /bin/bash
# Provision a new VM using virt-install

virt-install --name "test_windows_server_2016" \
             --memory 8192 \
             --arch "x86_64" \
             --vcpus 4 \
             --cpu host \
             --security type=dynamic \
             --clock offset=localtime \
             --pm suspend_to_mem=off,suspend_to_disk=off \
             --cdrom "/homePool/home/Downloads/OS/en_windows_server_2016_standard.iso" \
             --disk path=/homePool/home/VMs/server_2016_standard.raw,size=100 \
             --disk path=/homePool/home/VMs/server_2016_standard_additional.raw,size=500 \
             --network bridge=vmnet8
             --dry-run
