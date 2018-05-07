#! /usr/bin/env python
"""
Simple script to allow a user to obtain the list of neighbours and print them for both CDP/LLDP

Requires the ACI Toolkit: pip install acitoolkit

Based off:
https://github.com/datacenter/acitoolkit/blob/master/samples/aci-show-cdp.py
https://github.com/datacenter/acitoolkit/blob/master/samples/aci-show-lldp.py

Made various modifications to suit my needs

To Do:
    * Store in dictionary, with host+interface as key
    * Can then display per host / per port neighbor information
    * Be able to monitor these connections and if they differ during a subsequent run of the script, flag it to user

Michael Petrinovic 2018
"""
import acitoolkit.acitoolkit as aci


"""
Simple application that logs on to the APIC, pull all CDP neighbours,
and display in text table format
"""
import acitoolkit.acitoolkit as ACI
from acitoolkit import Node
from acitoolkit.aciConcreteLib import ConcreteCdp
from acitoolkit.aciConcreteLib import ConcreteLLdp
from tabulate import tabulate
import time

def main():
    """
    Main show Cdps routine
    :return: None
    """
    # Take login credentials from the command line if provided
    start_time = time.time()

    description = ('Simple application that logs on to the APIC'
                   'and displays all the CDP/LLDP neighbours.')
    creds = ACI.Credentials('apic', description)
    creds.add_argument('--protocol', choices=["cdp", "lldp", "both"], default="both", help='Choose if you want to see CDP/LLDP or both. Default is both')
    args = creds.get()

    # Login to APIC
    session = ACI.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        return
    else:
        print('%% Login to APIC: Successful')

    print ("Proceeding to next step...")
    print ("Retrieving node information...")
    nodes = Node.get_deep(session, include_concrete=True)
    cdp_count = 0
    lldp_count = 0

    if args.protocol == "both" or args.protocol == "cdp":
        print "Processing CDP Information..."
        cdps = []
        for node in nodes:
            node_concrete_cdp = node.get_children(child_type=ConcreteCdp)
            for node_concrete_cdp_obj in node_concrete_cdp:
                cdps.append(node_concrete_cdp_obj)

        tables = ConcreteCdp.get_table(cdps)
        cdp_list = []
        for table in tables:
            for table_data in table.data:
                #print table_data
                if table_data not in cdp_list:
                    cdp_list.append(table_data)
                    cdp_count += 1

        print ("=" * 100)
        print ("CDP: Total Entries [" + str(cdp_count) + "]")
        print ("=" * 100)
        print tabulate(cdp_list, headers=["Node-ID",
                                          "Local Interface",
                                          "Neighbour Device",
                                          "Neighbour Platform",
                                          "Neighbour Interface"])

    if args.protocol == "both" or args.protocol == "lldp":
        print "Processing LLDP Information..."
        lldps = []
        for node in nodes:
            node_concrete_lldp = node.get_children(child_type=ConcreteLLdp)
            for node_concrete_lldp_obj in node_concrete_lldp:
                lldps.append(node_concrete_lldp_obj)

        tables = ConcreteLLdp.get_table(lldps)
        lldp_list = []
        for table in tables:
            for table_data in table.data:
                #print table_data
                if table_data not in lldp_list:
                    lldp_list.append(table_data)
                    lldp_count += 1

        print ("=" * 100)
        print ("LLDP: Total Entries [" + str(lldp_count) + "]")
        print ("=" * 100)
        print(tabulate(lldp_list, headers=["Node-ID",
                                           "Ip",
                                           "Name",
                                           "Chassis_id_t",
                                           "Neighbour Platform",
                                           "Neighbour Interface"]))

    print("--- Execution Time: %s seconds ---" % (time.time() - start_time))

if __name__ == '__main__':
    main()
