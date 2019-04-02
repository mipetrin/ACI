ENDPOINT

This script will make the relevant API calls in order to extract the list of Endpoints within your ACI Fabric. It will then also perform an additional OUI MAC Address Lookup to identify what are the hardware vendors of the Endpoints to help identify what is connected to your ACI Fabric.

> It will then produce a simple report for you, that includes all the following; MAC Address, MAC Vendor, IP Address, Interface, Encap, Tenant, App Profile, End Point Group

It can be executed via the following:
* -u is your APIC cluster
* -l is your login username

```YAML
# python aci_endpoints_with_vendor.py -u https://10.66.80.242 -l mipetrin  
```


Created by Michael Petrinovic 2018


WARNING:

These scripts are meant for educational/proof of concept purposes only - as demonstrated at Cisco Live and/or my other presentations. Any use of these scripts and tools is at your own risk. There is no guarantee that they have been through thorough testing in a comparable environment and I am not responsible for any damage or data loss incurred as a result of their use
