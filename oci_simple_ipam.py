import ipaddress

try:
    from tabulate import tabulate
except ModuleNotFoundError:
    print("ERROR: Install tabulate for table output.")
    print("From PIP: pip3 install tabulate --user")
    quit(-1)

try: 
    import oci
except ImportError: 
    print("The OCI SDK needs to be installed before this script will work.")
    quit(-1)

config = oci.config.from_file()
core_client = oci.core.VirtualNetworkClient(config)
resource_search_client = oci.resource_search.ResourceSearchClient(config)
search_resources_response = resource_search_client.search_resources(
    search_details=oci.resource_search.models.StructuredSearchDetails(type="Structured",query="query subnet resources"))

#For each subnet in from the search response query, make some smart decisions.
high_utilization_subnets=[]
for i in range(len(search_resources_response.data.items)):
    #Variables For API Data
    subnet_ocid=(search_resources_response.data.items[i].identifier)
    get_subnet_response = core_client.get_subnet(subnet_id=subnet_ocid)
    list_private_ips_response = core_client.list_private_ips(subnet_id=subnet_ocid)

    #Give the user feedback on the progress.
    print("({}/{}) - Collecting Data for SUBNET-{}".format(i+1, len(search_resources_response.data.items), get_subnet_response.data.display_name))

    #Find the Active IP addresses in the subnet.
    #Reserved IP addresses are added here (Gateway, Network and Broadcast Address)
    active_ip_addresses=[]
    active_ip_addresses.append({"IP Address": ipaddress.ip_network(get_subnet_response.data.cidr_block)[0], "Display Name": "NETWORK_ADDRESS--OCI_RESERVED"})
    active_ip_addresses.append({"IP Address": ipaddress.ip_network(get_subnet_response.data.cidr_block)[1], "Display Name": "GATEWAY_ADDRESS--OCI_RESERVED"})
    for i in range(len(list_private_ips_response.data)):
        active_ip_addresses.append({"IP Address": list_private_ips_response.data[i].ip_address, "Display Name": list_private_ips_response.data[i].display_name})
    active_ip_addresses.append({"IP Address": ipaddress.ip_network(get_subnet_response.data.cidr_block)[-1], "Display Name": "BROADCAST_ADDRESS--OCI_RESERVED"})
    #print(tabulate(active_ip_addresses, headers="keys"))

    #Variables for Subnet Utilization
    num_available_ip_addresses=(ipaddress.ip_network(get_subnet_response.data.cidr_block).num_addresses)
    num_active_ip_addresses=(len(active_ip_addresses))
    num_utilization=(num_active_ip_addresses/num_available_ip_addresses*100)
    
    #Output to a dictionary
    utilization_dictionary={}
    utilization_dictionary['SUBNET_NAME']=(get_subnet_response.data.display_name)
    utilization_dictionary['SUBNET_SIZE']=(num_available_ip_addresses)
    utilization_dictionary['ACTIVE_IPS']=(num_active_ip_addresses)
    utilization_dictionary['UTILIZATION']=("{}%".format(round(num_utilization)))
    #print(utilization_dictionary)

    #Warn About Subnets with High Utilization
    if num_utilization > 75:
        high_utilization_subnets.append(utilization_dictionary)

print("")
print("")
print("")
print("Here are the subnets with high utilization")
print("")
print(tabulate(high_utilization_subnets, headers="keys"))
print("")
print("You can see the active IP addresses and utilization of all subnets by uncommenting the print statements in the script.")
