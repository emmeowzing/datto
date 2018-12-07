#! /bin/bash
# Generate a new client's keys with all of the defaults

if [ $# -ne 1 ]
then
    printf "Expected one argument, received %s\\n" "$#"
    exit 1
fi

name="$1"
OUTDIR="/home/ubuntu/tocopy"

source "/etc/openvpn/easy-rsa/vars"

# Per build-key, this is the same as
# /etc/openvpn/easy-rsa/pkitool --interact "some string containing all of the arguments"
/etc/openvpn/easy-rsa/build-key "$name"

rm "$OUTDIR/"*

sleep 0.5

for file in "/etc/openvpn/easy-rsa/keys/$name".*
do
   mv "$file" "$OUTDIR"
done

cp /etc/openvpn/easy-rsa/keys/ca.crt "$OUTDIR"
cp /etc/openvpn/easy-rsa/keys/ta.key "$OUTDIR"

chmod 644 "$OUTDIR/"*

# Now generate a really quick and dirty client.conf file.
# $ cat /etc/openvpn/client.conf | awk '{ if ($0 !~ /^\#/ && $0 !~ /^;/ && length($0) != 0) { print $0 } }'

printf "client\\ndev tun\\nproto udp\\nremote ec2-18-224-16-221.us-east-2.compute.amazonaws.com 1194\\nresolv-retry infinite\\nnobind\\npersist-key\\npersist-tun\\nhttp-proxy-retry\\nca /etc/openvpn/ca.crt\\ncert /etc/openvpn/%s.crt\\nkey /etc/openvpn/%s.key\\nremote-cert-tls server\\ntls-auth /etc/openvpn/ta.key 1\\ncipher AES-256-CBC\\nverb 3\\n" "$name" "$name" > "$OUTDIR/client.conf"

printf "Command to copy all of these files:\\n\\n"
printf "\\tscp -i ~/.ssh/OpenVPN_Key_Pair.pem ubuntu@ec2-18-224-16-221.us-east-2.compute.amazonaws.com:tocopy/{ca.crt,client.conf,%s.crt,%s.csr,%s.key,ta.key} /etc/openvpn/\\n\\n" "$name" "$name" "$name"
