Simple application that logs on to the APIC and displays all the CDP/LLDP neighbours.

> It will then produce a simple report for you, that includes all the following; ACI Fabric Node, ACI Fabric Interface, Name of the connected Device, Neighbor Platform, Neighbor Interface


It can be executed via the following:
* -u is your APIC cluster
* -l is your login username
*   --protocol {cdp,lldp,both}   Choose if you want to see CDP/LLDP or both. Default is both

```YAML
# python aci_neighbours.py -u https://10.66.80.242 -l mipetrin --protocol both
```


Created by Michael Petrinovic 2018


WARNING:

These scripts are meant for educational/proof of concept purposes only - as demonstrated at Cisco Live and/or my other presentations. Any use of these scripts and tools is at your own risk. There is no guarantee that they have been through thorough testing in a comparable environment and I am not responsible for any damage or data loss incurred as a result of their use
