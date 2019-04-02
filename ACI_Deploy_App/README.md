This script will allow you to deploy an Application to an ACI Fabric.

> It will configure the Tenant / App Profile / EPG / BD / VRF

It can be executed via the following:
* --url is your APIC cluster
* --login is your login username
* --prefix what you want all items to have as a prefix
* --amount how many Tenants would you like to create
* --delete Boolean flag. If present, script will delete the tenants and configuration - with warning for each tenant

```YAML
# python deploy_aci_app.py --url https://10.66.80.38 --login admin --prefix mipetrin-CLUS18 --amount 3
# python deploy_aci_app.py --url https://10.66.80.38 --login admin --prefix mipetrin-CLUS18 --amount 3 -delete

```


Created by Michael Petrinovic 2018


WARNING:

These scripts are meant for educational/proof of concept purposes only - as demonstrated at Cisco Live and/or my other presentations. Any use of these scripts and tools is at your own risk. There is no guarantee that they have been through thorough testing in a comparable environment and I am not responsible for any damage or data loss incurred as a result of their use
