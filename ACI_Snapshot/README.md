Simple application that will connect to the ACI Fabric and create a Snapshot of the Fabric. It will be stored either on the APIC or in a pre-configured "remote" location

> NOTE that the Remote Location must already exist and be correctly configured within the APIC. You then must call it exactly how it is displayed in the APIC

It can be executed via the following:
* -u is your APIC cluster
* -l is your login username
*  --target {apic,remote}
                        The location where you would like the snapshot to be saved

```YAML
# python aci_faults.py -u https://10.66.80.242 -l mipetrin --target apic
```


Created by Michael Petrinovic 2018


WARNING:

These scripts are meant for educational/proof of concept purposes only - as demonstrated at Cisco Live and/or my other presentations. Any use of these scripts and tools is at your own risk. There is no guarantee that they have been through thorough testing in a comparable environment and I am not responsible for any damage or data loss incurred as a result of their use
