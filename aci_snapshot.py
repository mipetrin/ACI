#! /usr/bin/env python
"""
Simple script to allow user to utilise the Snapshot manager and take configuration backup to a remote location

NOTE: This script simply pushes the JSON config to the Snapshot manager on the APIC.
The APIC then takes over to execute the request


Requires the ACI Toolkit: pip install acitoolkit

USAGE:
# python aci_snapshot.py -u https://10.66.80.242 -l mipetrin

Michael Petrinovic 2018
"""
import acitoolkit.acitoolkit as aci

def main():
    description = ('Simple application that logs on to the APIC and displays the AAA logs')
    creds = aci.Credentials('apic', description)
    args = creds.get()

    # Login to APIC
    session = aci.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        exit(0)

    base_url = '/api/node/mo/uni/fabric/configexp-defaultOneTime.json'
    my_url = args.url + base_url

    print("\nAPI Call to URL:")
    print(my_url + "\n")

    payload = {
        "configExportP":{
            "attributes":{
                "dn":"uni/fabric/configexp-defaultOneTime",
                "name":"defaultOneTime",
                "snapshot":"false",
                "targetDn":"", # Leave blank for entire Fabric
                "adminSt":"triggered", # We want to execute immediately
                "rn":"configexp-defaultOneTime",
                "status":"created,modified",
                "descr":"mike-test-snapshot-2" # Description
            },
            "children":[{
                "configRsRemotePath":{
                    "attributes":{
                        "tnFileRemotePathName":"Mike-FTP", # Must be a valid existing remote location
                        "status":"created,modified"
                    },
                "children":[]
                }
            }]
        }
    }

    resp = session.push_to_apic(base_url, data=payload)
    #response = resp.json()
    #print response

    if resp.ok:
        print ("Successfully pushed the configuration request to the APIC")

    if not resp.ok:
        print('%% Error: Could not push configuration to APIC')
        print(resp.text)

if __name__ == '__main__':
    main()



'''
RAW API call, could be used in POSTMAN instead of this Python Script

POST: https://apic1.mike.local/api/node/mo/uni/fabric/configexp-defaultOneTime.json
{
    "configExportP":{
        "attributes":{
            "dn":"uni/fabric/configexp-defaultOneTime",
            "name":"defaultOneTime",
            "snapshot":"false",
            "targetDn":"",
            "adminSt":"triggered",
            "rn":"configexp-defaultOneTime",
            "status":"created,modified",
            "descr":"mike-test-snapshot-2"
        },
        "children":[{
            "configRsRemotePath":{
                "attributes":{
                    "tnFileRemotePathName":"Mike-FTP",
                    "status":"created,modified"
                },
            "children":[]
            }
        }]
    }
}
'''
