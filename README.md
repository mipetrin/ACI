Created by Michael Petrinovic 2018

Sample ACI Python Scripts for
* Cisco Live Melbourne 2018: BRKDCN-2602
* Cisco Live Orlando 2018: BRKDCN-2011
* Cisco Live Barcelona 2019: BRKDCN-2011

Sample Usage:

```YAML
# python aci_endpoints_with_vendor.py -u https://10.66.80.242 -l mipetrin  

# python aci_neighbours.py -u https://10.66.80.242 -l mipetrin   [help, two options cdp | lldp or default is both]

# python aci_faults.py -u https://10.66.80.242 -l mipetrin

# python aci_login_analyzer.py -u https://10.66.80.242 -l mipetrin --help
# python aci_login_analyzer.py -u https://10.66.80.242 -l mipetrin --action login --user root
# python aci_login_analyzer.py -u https://10.66.80.242 -l mipetrin --action login --user root --start 2018-02-28T00:00 --end 2018-03-08T23:59
# python aci_login_analyzer.py -u https://10.66.80.242 -l mipetrin --result Failure --start 2018-02-28T00:00 --end 2018-03-08T23:59 --user UNKNOWN

# python aci_search_aaaModLR.py -u https://10.66.80.38 -l admin --user admin    [ help option ]
# python aci_search_aaaModLR.py -u https://10.66.80.38 -l admin --user admin --start 2018-02-28T00:00 --end 2018-03-08T23:59
# python aci_search_aaaModLR.py -u https://10.66.80.38 -l admin --user admin --action deletion

# python deploy_aci_app.py --url https://10.66.80.38 --login admin --prefix mipetrin-CLUS18 --amount 3
# python deploy_aci_app.py --url https://10.66.80.38 --login admin --prefix mipetrin-CLUS18 --amount 3 -delete
```

WARNING:

These scripts are meant for educational/proof of concept purposes only - as demonstrated at Cisco Live and/or my other presentations. Any use of these scripts and tools is at your own risk. There is no guarantee that they have been through thorough testing in a comparable environment and I am not responsible for any damage or data loss incurred as a result of their use
