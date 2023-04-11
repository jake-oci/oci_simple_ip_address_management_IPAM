import oci
import ipaddress
import time
import argparse

try:
    from tabulate import tabulate
except ModuleNotFoundError:
    print("WARNING: Install tabulate to get verbose output.")
    print("From PIP: pip3 install tabulate")
    print("")
    time.sleep(2)

try: 
    import oci
except ImportError: 
    print("The OCI SDK needs to be installed before this script will work.")
    quit(-1)

CLI=argparse.ArgumentParser()
CLI.add_argument("--compartment_ocid", "-c", type=str,help="Specify your Compartment OCID",required=True)
CLI.add_argument("--verbose", "-r", action='store_true',help="Show a table of all of the IP's used in the Subnet.")
args=CLI.parse_args()

#Add Argparse for compartmentId
#COMPARTMENT_ID="ocid1.compartment.oc1..aaaaaaaa3pyxiqdebxgd6ja2dzsemmhnstxxrzb3lqgdxtzfapmvbubisuza"

config = oci.config.from_file()
core_client = oci.core.VirtualNetworkClient(config)
list_subnets_response = core_client.list_subnets(compartment_id=args.compartment_ocid)

#I can't unpack the list using data[*], so I unpack the list based on the number of items that are in the list.
list_of_subnets=[]
for i in range(len(list_subnets_response.data)):
    list_of_subnets.append(list_subnets_response.data[i].id)

#Get CIDR Block for each subnet
for subnet_ocid in list_of_subnets:
    #API Commands to get the CIDR block of the subnet and list the private IP's in use.
    get_subnet_response = core_client.get_subnet(subnet_id=subnet_ocid)
    list_private_ips_response = core_client.list_private_ips(subnet_id=subnet_ocid)
    subnet_cidr_block=get_subnet_response.data.cidr_block
    subnet_cidr_total_addrs=ipaddress.ip_network(subnet_cidr_block).num_addresses
    
    #Find the Active IP addresses in the subnet.
    #Reserved IP addresses are added here (Gateway, Network and Broadcast Address)
    active_ip_addresses=[]
    active_ip_addresses.append({"IP Address": ipaddress.ip_network(subnet_cidr_block)[0], "Display Name": "OCI_RESERVED_NETWORK"})
    active_ip_addresses.append({"IP Address": ipaddress.ip_network(subnet_cidr_block)[1], "Display Name": "OCI_RESERVED_GATEWAY"})
    for i in range(len(list_private_ips_response.data)):
        active_ip_addresses.append({"IP Address": list_private_ips_response.data[i].ip_address, "Display Name": list_private_ips_response.data[i].display_name})
    active_ip_addresses.append({"IP Address": ipaddress.ip_network(subnet_cidr_block)[-1], "Display Name": "OCI_RESERVED_BROADCAST"})
    print("SUBNET NAME - {}".format(get_subnet_response.data.display_name))
    if args.verbose is True:
        print(tabulate(active_ip_addresses, headers="keys"))
    print("Total Free IP's in {} -- {}/{}".format(get_subnet_response.data.display_name, len(active_ip_addresses), subnet_cidr_total_addrs))
    print("")
