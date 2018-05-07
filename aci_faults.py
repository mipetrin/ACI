#! /usr/bin/env python
"""
Simple script to allow a user to obtain the list of active Fault Instances in an ACI Fabric

Requires the ACI Toolkit: pip install acitoolkit

To Do:
    # Perhaps change this to also do all by default, or allow user to specify severity
    # Give user the option to specify the time range that they are interested in for faults

Michael Petrinovic 2018
"""
import acitoolkit.acitoolkit as aci
from operator import itemgetter
from tabulate import tabulate

def query_fault(handle, sev, sort):
    '''
    Custom function to return the set of faultInst objects that match the severity
    '''
    # /api/node/class/faultInst.xml?query-target-filter=and(eq(faultInst.severity,"minor"))
    base_url = '/api/node/class/faultInst.json?'

    # Sort by last Transition time. Either Ascending or Descending order
    sort_order = 'order-by=faultInst.lastTransition|%s' % (sort) # asc | desc

    # URL for a faultInst lookup, with severity variable
    query_target_filter = '&query-target-filter=and(eq(faultInst.severity,"%s"))' % (sev)
    my_url = base_url + sort_order + query_target_filter

    #print("\nAPI Call to URL:")
    #print(my_url + "\n")

    ret = handle.get(my_url)
    response = ret.json()
    return response

def print_fault(severity, mo_list):
    '''
    Custom function to print the list of faults, using the format of my choosing
    In order to modify the order in the list, change the order from the section within main()
    prior to calling this print_fault
    '''
    print "=" * 80
    print ("[" + severity + "] Faults Summary. Total = " + str(len(mo_list)))
    print "=" * 80

    # Check if the list is empty or not
    if len(mo_list) >= 1:
        for mo in mo_list:
            print ("# [" + mo[0] + "] : [Description = " + mo[1] + "] [Cause: " + mo[2] + "] [Occurence: " + mo[3] + "] [Last Transition: " + mo[4] + "]")

    else:
        print ("N/A")


def main():
    '''
    Main Routine
    '''
    # Take login credentials from the command line if provided
    description = ('Simple application to display details about faults in an ACI Fabric')
    creds = aci.Credentials('apic', description)
    creds.add_argument('--sort', choices=["asc", "desc"], default="desc", help='Specify the sort order within each severity based on time/date. Default is Descending order. i.e. Newest faults at the top of each category')

    args = creds.get()

    # Login to APIC
    session = aci.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        return

    # Available severity codes for ACI Fault Instances
    fault_severity = ["critical", "major", "minor", "warning", "info", "cleared"]

    fault_lookup = {} # Dictionary to be used to store the returned MO's, with the key being the severity
    fault_severity_count = {} # Dictionary to track total faults per severity

    # Loop through all fault severity types, perform a fault lookup in the system and return the list of MO's.
    # Assign to the fault_lookup dictionary, with severity as the key
    for fault_type in fault_severity:
        resp = query_fault(session, fault_type, args.sort)
        resp2 = resp['imdata']
        faultInst = []
        for entry in resp2:
            faultInst.append((entry["faultInst"]["attributes"]["code"],
                              entry["faultInst"]["attributes"]["descr"],
                              entry["faultInst"]["attributes"]["cause"],
                              entry["faultInst"]["attributes"]["occur"],
                              entry["faultInst"]["attributes"]["lastTransition"]))

        #print faultInst
        fault_lookup[fault_type] = faultInst
        # Find out the length of the inner list, based off the fault severity in the lookup
        # eg: fault_lookup["critical"] = [x,y,z]
        fault_severity_count[fault_type] = len(fault_lookup[fault_type])

    # Loop through each severity, sort by faultCode and then print it out
    for item in fault_severity:
        print_fault(item, fault_lookup[item])

    print "=" * 80
    print ("Summary of total faults")
    print "-" * 80
    for fault_summary in fault_severity:
        print (fault_summary + " = " + str(fault_severity_count[fault_summary]))
    print "=" * 80


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
