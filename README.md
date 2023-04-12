# oci_simple_ip_address_management_IPAM 
Use Cases:
1.) Find the high utilization subnets of your OCI tenancy.
2.) Find the current IP addresses assigned for each subnet.
3.) Find the utilization of all subnets in your OCI tenancy. 

Option 2 and Option 3 are "optional" and the print statements within the script can be uncommented to see the data. They are uncommented by default because there is a lot of noise generated when setting these options for large environments. Long term, this script will be able to take the data in tabular format and output it as a CSV/HTML for more parsing.

# Grab it
https://github.com/jake-oci/oci_simple_ip_address_management_IPAM

# Run it

Make sure tabluate is installed
-pip3 install tabulate

Run the script
-./oci_simple_ip_address_management_IPAM/oci_simple_ipam.py

Let it fly!
