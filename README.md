# OCI_Lite_IPAM
Find out how many free IP's are left on your OCI subnet

# Grab it
git clone https://github.com/jake-oci/OCI_Lite_IPAM

# Run it
python3 free_ips.py --compartment_ocid COMPARTMENT_OCID

If you want verbose output make sure that "tabulate" installed, and add the --verbose option to your CLI argument.
python3 free_ips.py --compartment_ocid COMPARTMENT_OCID --verbose
