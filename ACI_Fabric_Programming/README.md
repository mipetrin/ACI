This script can be used to check that various elements are correctly programmed within an ACI Environment


Current Checks available:
* EPG_VXLAN_ENCAP = Identify if the EPG (VXLAN encap) is consistent across the Fabric
* BD_VXLAN_ENCAP = Identify if the BD (VXLAN encap) is consistent across the Fabric
* VZANY_MISSING = Identify if the vzAny contract is missing from a Tenant/VRF across the Fabric
* EPG_ENCAP_MISSING = Identify if the EPG (VLAN Encap) is missing from any nodes across the Fabric
* EPG_BD_MAPPING = Identify if the EPG to BD mapping is correct when comparing GUI output and node programming across the Fabric
* ALL = Execute all above checks 

> It will then produce a simple report for you, that includes all various points of information to help you determine if/where the issues are occurring. 


It can be executed via the following:
* -u is your APIC cluster
* -l is your login username
*  --list                Print out the list of checks that can be performed
*  --debug               Enable debugging output to screen
*  --check {EPG_VXLAN_ENCAP,BD_VXLAN_ENCAP,VZANY_MISSING,EPG_ENCAP_MISSING,EPG_BD_MAPPING,ALL}
                        Specify which checks to perform. Default = all

```YAML
# python fabric_programming.py -u https://10.66.80.242 -l mipetrin --check ALL
```


Created by Michael Petrinovic 2019


WARNING:

These scripts are meant for educational/proof of concept purposes only - as demonstrated at Cisco Live and/or my other presentations. Any use of these scripts and tools is at your own risk. There is no guarantee that they have been through thorough testing in a comparable environment and I am not responsible for any damage or data loss incurred as a result of their use