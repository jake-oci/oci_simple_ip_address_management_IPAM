import argparse, concurrent.futures, ipaddress, oci, time

class ip_address_management():
    
    def __init__(self):
        # Data
        self.timer = time.time()
        self.subnet_details_dict = {} # Contatination of API subnet data.
        self.high_utilization_subnets_dict = {} # Dictionary of regions with highly utilized subnets.
        self.regional_api_clients_dict = {} # API Client for each region.
        self.regional_subnet_search_dict = {} # Prerequisit subnet data for each region.
        self.subscribed_regions = None # Regions the tenancy is subscribed to.

        # OCI SDK Auth and Config
        self.config = oci.config.from_file()
        self.config['retry_strategy'] = oci.retry.DEFAULT_RETRY_STRATEGY

        # Initiating Functions
        self.region_subscriptions()

        # Argparse Configuration
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('--region', '-r', nargs='+', help="Focus collection on specific regions. EXAMPLE: us-ashburn-1 or iad")
        self.parser.add_argument('--show_region', action='store_true', help="Show the regional subscriptions.")

        self.args = self.parser.parse_args()

        if self.args.show_region: # Show the subscribed regions for this tenant and then quit the script.
            subscribed_region_output = self.show_region()
            print(f"Subscribed to the following regions {subscribed_region_output}")
            quit(-1)
        
        if self.args.region: # If the --region parameter is passed, limit the output to the regions specified. 
            print(f"Output will be limited to the regions requested, {self.args.region}.")
            self.specify_regions()

        # Other Required Functions
        self.regional_api_client() # Build the service clients for each region.
        self.enumerate_subnet_data() # Find all the subnets in all regions.
        self.data_analysis() # Analyize the data and report highly utilized subnets.
    
    def data_output(self):
        try:
            from tabulate import tabulate

        except Exception: 

            print("ERROR: Install tabulate for table output.")
            print("From PIP: pip3 install tabulate --user")

            raise Exception
            
        for region, subnets in self.high_utilization_subnets_dict.items():
            print("")
            print(f"***{region.upper()}***")
            print(tabulate(self.high_utilization_subnets_dict[region], headers="keys"))

    def specify_regions(self):
        specified_region_list = []

        for specified_region in self.args.region:
            region_match = False

            for index, sub_region in enumerate(self.subscribed_regions):

                if sub_region.region_name.lower() == specified_region.lower():
                    specified_region_list.append(self.subscribed_regions[index])
                    region_match = True

                if sub_region.region_key.lower() == specified_region.lower():
                    specified_region_list.append(self.subscribed_regions[index])
                    region_match = True
            
            if region_match is False:
                print(f"Synax issue, unable to find '{specified_region}', verify your region syntax.")
                raise Exception

        self.subscribed_regions = specified_region_list

    # Show subscribed Regions
    def show_region(self):
        region_list = []

        for region in self.subscribed_regions:
            region_list.append(region.region_name)

        return(region_list)

    # API Service Client Builder
    def regional_api_client(self):

        for oci_region in self.subscribed_regions:

            self.regional_api_clients_dict[oci_region.region_name] = {}

            clients_to_build = [oci.core.VirtualNetworkClient, oci.resource_search.ResourceSearchClient]

            for client in clients_to_build:

                api_client = client(self.config)
                api_client.base_client.set_region(oci_region.region_name)
                self.regional_api_clients_dict[oci_region.region_name][client.__name__] = api_client

    # List each subnet in each region.
    def regional_subnet_search(self, oci_region):
        
        search_resources_response = self.regional_api_clients_dict[oci_region]['ResourceSearchClient'].search_resources(
            search_details=oci.resource_search.models.StructuredSearchDetails(
                type = "Structured",
                query = "query subnet resources")
                ).data
        
        self.regional_subnet_search_dict[oci_region] = search_resources_response

    # List the regions that the tenancy is subscribed to.
    def region_subscriptions(self):

        api_client = oci.identity.IdentityClient(self.config)

        self.subscribed_regions = oci.pagination.list_call_get_all_results(
            api_client.list_region_subscriptions, self.config['tenancy']).data
        
    # Find the details of each subnet within the region.
    def subnet_details(self, subnet_ocid, oci_region):

        get_subnet_response = self.regional_api_clients_dict[oci_region]['VirtualNetworkClient'].get_subnet(subnet_id=subnet_ocid).data
        self.subnet_details_dict[oci_region][subnet_ocid]['subnet_details'] = get_subnet_response

    # Find the private IP address of each subnet within the region.
    def private_ip_usage(self, subnet_ocid, oci_region):
        
        list_private_ips_response = self.regional_api_clients_dict[oci_region]['VirtualNetworkClient'].list_private_ips(subnet_id=subnet_ocid).data
        
        if len(list_private_ips_response) > 0:
            self.subnet_details_dict[oci_region][subnet_ocid]['private_ip_details'] = list_private_ips_response

    # Function to send 10 API calls at a time to each regional service client.
    def subnet_buildout_function(self, oci_region, data):

        api_thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=10)

        self.subnet_details_dict[oci_region] = {}

        for index, subnet in enumerate(data.items):

            self.subnet_details_dict[oci_region][subnet.identifier] = {}
            api_thread_pool.submit(self.subnet_details, subnet.identifier, oci_region)
            api_thread_pool.submit(self.private_ip_usage, subnet.identifier, oci_region)
        
        api_thread_pool.shutdown(wait=True)
    
    def data_analysis(self):
        for region, regional_subnet in self.subnet_details_dict.items():
            for subnet_ocid, subnet_data in regional_subnet.items():
                if 'private_ip_details' in subnet_data:
                    if 'subnet_details' in subnet_data:
                        self.subnet_utilization_analysis(subnet_data['subnet_details'], subnet_data['private_ip_details'], region)

    def enumerate_subnet_data(self):

        thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=len(self.subscribed_regions))
        
        for sub_region in self.subscribed_regions:
            thread_pool.submit(self.regional_subnet_search, sub_region.region_name)

        thread_pool.shutdown(wait=True)

        # Enumerate each subnet with additional data.

        thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=len(self.subscribed_regions))

        for region, subnet_search_data in self.regional_subnet_search_dict.items():

            thread_pool.submit(self.subnet_buildout_function, region, subnet_search_data)

        thread_pool.shutdown(wait=True)

    # Analysis of the API Data
    def subnet_utilization_analysis(self, subnet_details, private_ip_details, region):
        # Find the Active IP addresses in the subnet.
        # Reserved IP addresses are added here (Gateway, Network and Broadcast Address) in addition to the workload IP's.
        active_ip_addresses = []
        active_ip_addresses.append({"IP Address": ipaddress.ip_network(subnet_details.cidr_block)[0], "Display Name": "NETWORK_ADDRESS--OCI_RESERVED"})
        active_ip_addresses.append({"IP Address": ipaddress.ip_network(subnet_details.cidr_block)[1], "Display Name": "GATEWAY_ADDRESS--OCI_RESERVED"})
        
        for index, private_ip_addr in enumerate(private_ip_details):
            active_ip_addresses.append({"IP Address": private_ip_addr.ip_address, "Display Name": private_ip_addr.display_name})
        
        active_ip_addresses.append({"IP Address": ipaddress.ip_network(subnet_details.cidr_block)[-1], "Display Name": "BROADCAST_ADDRESS--OCI_RESERVED"})

        # Variables for Subnet Utilization
        num_available_ip_addresses = ipaddress.ip_network(subnet_details.cidr_block).num_addresses
        num_active_ip_addresses = len(active_ip_addresses)
        num_utilization = num_active_ip_addresses/num_available_ip_addresses*100
        
        # Output to a dictionary
        utilization_dictionary={}
        utilization_dictionary['SUBNET_NAME'] = subnet_details.display_name
        utilization_dictionary['SUBNET_SIZE'] = num_available_ip_addresses
        utilization_dictionary['ACTIVE_IPS'] = num_active_ip_addresses
        utilization_dictionary['UTILIZATION'] = f"{round(num_utilization)}%"

        # Warn About Subnets with High Utilization
        if num_utilization >= 50:
            if region in self.high_utilization_subnets_dict:
                self.high_utilization_subnets_dict[region].append(utilization_dictionary)
            else:
                self.high_utilization_subnets_dict[region] = []
                self.high_utilization_subnets_dict[region].append(utilization_dictionary)

if __name__ == '__main__':

    print("Collecting Subnet Utilization Statistics")

    ipam_module = ip_address_management()

    # Show how long the script took to execute.
    print(f"Data collection took {round(time.time()-ipam_module.timer, 1)} seconds")

    print("")
    print("Here are the subnets with high utilization")
    print("")

    # Output the data to a table on the screen.
    ipam_module.data_output()
