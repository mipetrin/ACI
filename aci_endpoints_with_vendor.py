#!/usr/bin/env python
#
#
# Michael Petrinovic 2018
#
# APIC login username: mipetrin
# APIC URL: https://10.66.80.242
# APIC Password: cisco
#
"""
Simple application to display details about endpoints
"""
import acitoolkit.acitoolkit as aci
from tabulate import tabulate
import requests

def main():
    """
    Main Show Endpoints Routine
    """
    # Take login credentials from the command line if provided
    # Otherwise, take them from your environment variables file ~/.profile

    description = ('Simple application to display details about endpoints')
    creds = aci.Credentials('apic', description)
    args = creds.get()

    # Login to APIC
    session = aci.Session(args.url, args.login, args.password)
    # session = aci.Session(URL1, LOGIN1, PASSWORD1)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        return

    # Download all of the interfaces and store the data as tuples in a list
    data = []
    endpoints = aci.Endpoint.get(session)
    for ep in endpoints:
        epg = ep.get_parent()
        app_profile = epg.get_parent()
        tenant = app_profile.get_parent()

        # Check each MAC address via API call to macvendors.com to identify hardware vendor
        url = "http://api.macvendors.com/" + ep.mac
        response = requests.request("GET", url)
        mac_vendor = response.text

        # Store in list as tuple, that will be printed in the tabulate format
        data.append((ep.mac, mac_vendor, ep.ip, ep.if_name, ep.encap,
                    tenant.name, app_profile.name, epg.name))

    # Display the data downloaded
    print tabulate(data, headers=["MACADDRESS", "MAC VENDOR", "IPADDRESS", "INTERFACE",
                                  "ENCAP", "TENANT", "APP PROFILE", "EPG"], tablefmt="simple")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
