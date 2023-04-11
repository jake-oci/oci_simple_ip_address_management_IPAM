subnet_ocid=
#
subnet_cidr_block=$(oci network subnet get --subnet-id $subnet_ocid --query 'data."cidr-block"' | tr -d "\"")
subnet_cidr_hosts=$(python3 -c "import ipaddress; print(ipaddress.ip_network('$subnet_cidr_block').num_addresses)")
subnet_cidr_used_ips=$(oci network private-ip list --subnet-id $subnet_ocid --query 'length(data[*]."ip-address")')
oci network private-ip list --subnet-id $subnet_ocid --query "data[*].{\"IP Address\":\"ip-address\",\"Instance Name\":\"display-name\"}" --output table \
&& echo "There are $((subnet_cidr_hosts - 3)) USEABLE IP's in the $subnet_cidr_block Subnet CIDR block, and $((subnet_cidr_hosts - subnet_cidr_used_ips - 3)) FREE IPs left."

#Test with a few services
#Public Load Balancer
#Bastion
#Other services that consume an IP
