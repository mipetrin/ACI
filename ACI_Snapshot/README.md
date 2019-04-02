SNAPSHOT

This script will make the relevant API calls in order to extract the list of ACI Faults currently active within an ACI Environment.

> It will then produce a simple report for you, that includes all the faults, what severity, how many occurrences, possible causes, etc.

It can be executed via the following:
* -u is your APIC cluster
* -l is your login username

```YAML
# python aci_faults.py -u https://10.66.80.242 -l mipetrin
```


Created by Michael Petrinovic 2018


WARNING:

These scripts are meant for educational/proof of concept purposes only - as demonstrated at Cisco Live and/or my other presentations. Any use of these scripts and tools is at your own risk. There is no guarantee that they have been through thorough testing in a comparable environment and I am not responsible for any damage or data loss incurred as a result of their use
