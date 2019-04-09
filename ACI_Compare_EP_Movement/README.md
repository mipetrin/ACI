This script enables you to identify if any endpoints have changed between captures. It allows you to take 2 captures of all the known Endpoints within your ACI Fabric (for example: during a maintenance window, before your changes and again after the changes). These each will be written to a file. The script will then compare the captures and identify:
* Endpoints that have moved
* Endpoints only in the "before" capture
* Endpoints only in the "after" capture

> For all Endpoints identified, it will report the following; Tenant, App Profile, EPG, MAC, Node, Interface, Encap

It can be executed via the following:
* -u is your APIC cluster
* -l is your login username
*  --debug {debug,info,warn,critical}
                        Enable debugging output to screen
*  --log                 Write the output to a log file: compare_ep_move.log.
                        Automatically adds timestamp to filename
*  --list                Print out the list of Tenants / App Profiles / EPGs
                        available to work with
*  --filter FILTER       Specify what to filter on. Eg: "tn-mipetrin" or "ap-
                        mipetrin-AppProfile". Use --list to identify what can
                        be used for filtering. Default = None
*  --pre PRE             Write the data to a file of your choosing. Specify
                        your prefix. Format will be JSON and this extension is
                        automatically added
*  --post POST           Write the data to a file of your choosing. Specify
                        your prefix. Format will be JSON and this extension is
                        automatically added
*  --compare COMPARE COMPARE
                        Compare the 2 files you specify. Be sure to pick a PRE
                        and POST file
*  --summary SUMMARY     Optionally, print out detailed summary of identified
                        Endpoints greater than x (provide totals per
                        Tenant/App/EPG/MAC/Encap)

```YAML
# python compare_ep_move.py -u https://10.66.80.242 -l mipetrin --list

# python compare_ep_move.py -u https://10.66.80.242 -l mipetrin --pre mike_test

# python compare_ep_move.py -u https://10.66.80.242 -l mipetrin --post mike_test

# python compare_ep_move.py -u https://10.66.80.242 -l mipetrin --post mike_test --filter "tn-mipetrin"

# python compare_ep_move.py -u https://10.66.80.242 -l mipetrin --compare mike_test_PRE.json mike_test_POST.json

# python compare_ep_move.py -u https://10.66.80.242 -l mipetrin --compare mike_test_PRE.json mike_test_POST.json --summary 20 --debug debug --log
```

> Be sure to also check out the awesome [Enhanced Endpoint Tracker](https://aci-enhancedendpointtracker.readthedocs.io/en/latest/introduction.html) written by Andy Gossett, as it is well tested and works on a lot more scenarios.


Created by Michael Petrinovic 2019


WARNING:

These scripts are meant for educational/proof of concept purposes only - as demonstrated at Cisco Live and/or my other presentations. Any use of these scripts and tools is at your own risk. There is no guarantee that they have been through thorough testing in a comparable environment and I am not responsible for any damage or data loss incurred as a result of their use