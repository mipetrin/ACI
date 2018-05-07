#! /usr/bin/env python
"""
Simple script to allow user to

Requires the ACI Toolkit: pip install acitoolkit

To Do:
    * Analyse data from aaaSessionLR
        * see who is logging into the system, how many times.
        * Count logins/logouts/refresh (trig). Look at the (descr) to get some more details.
    * If user is unknown and description contains Failure.
        * Means user has attempted to log in without a valid user on the system == worth to follow up
    * If user is defined/known and description contains Failure.
        * Means valid user but incorrect password. Could be a simple typo.
        * If, however, see many similar login attempts in short succession WITHOUT a successful login to break it up
        * FLAG, worth to follow up
    * If user is root, either successful or not
        * BE AFRAID unless working with TAC

Michael Petrinovic 2018
"""
import acitoolkit.acitoolkit as aci
from tabulate import tabulate
import re

def main():
    description = ('Simple application that logs on to the APIC and displays the AAA logs')
    creds = aci.Credentials('apic', description)
    creds.add_argument('--start', help='Start Date/Time for the search until either --end date/time or current date/time. Full Format: 2018-02-23T08:14:25')
    creds.add_argument('--end', help='End Date/Time for the search until either --start date/time or the beginning of the records. Full Format: 2018-02-23T08:14:25')
    creds.add_argument('--user', help='Find records for a specific user. Default is all. Use "UNKNOWN" to see unknown attempts. Can also look for "root"')
    creds.add_argument('--action', choices=["login", "logout", "refresh"], help='Find records for this specific action. Default is all')
    creds.add_argument('--result', choices=["Success", "Failure"], help='Specify an result to filter on. Default is all')
    creds.add_argument('--sort', choices=["asc", "desc"], default="desc", help='Specify the sort order. Default is Descending. i.e. Newest logs at the top')
    creds.add_argument('--debug', action='store_true', help='Print debug output')
    args = creds.get()

    # Login to APIC
    session = aci.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        exit(0)

    # ACI Query Target Filters:
    # https://www.cisco.com/c/en/us/td/docs/switches/datacenter/aci/apic/sw/2-x/rest_cfg/2_1_x/b_Cisco_APIC_REST_API_Configuration_Guide/b_Cisco_APIC_REST_API_Configuration_Guide_chapter_01.html

    base_url = '/api/node/class/aaaSessionLR.json?'

    # Sort by creation time. Either Ascending or Descending order
    sort_order = 'order-by=aaaSessionLR.created|%s' % (args.sort) # asc | desc

    # Build out the custom query-target-filter
    #if not (args.start and args.end and args.user and args.action and args.result) is None:
    if (args.start is None) and (args.end is None) and (args.user is None) and (args.action is None) and (args.result is None):
        print "\nNo custom filter selected\n"
        my_url = base_url + sort_order
    else:
        print "\nAt least one custom filter is selected\n"
        query_target_filter = '&query-target-filter=and('
        custom_filter = []

        if not(args.start is None):
            # Meaning it is set
            custom_filter.append('gt(aaaSessionLR.created,"%s")' % (args.start))
            if args.debug: print custom_filter

        if not(args.end is None):
            # Meaning it is set
            custom_filter.append('lt(aaaSessionLR.created,"%s")' % (args.end))
            if args.debug: print custom_filter

        if not(args.user is None):
            # Meaning it is set
            # Check if CLI arg user = UNKNOWN. If so, need to modify query to return
            # everything, then filter on UNKNOWN during printing only
            # This is because can't search on blank wildcard
            if args.user == "UNKNOWN":
                #custom_filter.append('wcard(aaaSessionLR.user, "")')
                pass
            else:
                custom_filter.append('wcard(aaaSessionLR.user, "%s")' % (args.user))
                if args.debug: print custom_filter

        if not(args.result is None):
            # Meaning it is set
            custom_filter.append('wcard(aaaSessionLR.descr,"%s")' % (args.result))
            if args.debug: print custom_filter

        if not(args.action is None):
            # Meaning it is set
            custom_filter.append('wcard(aaaSessionLR.trig,"%s")' % (args.action))
            if args.debug: print custom_filter

        query_target_filter_end = ')'
        if args.debug: print custom_filter

        count = 1
        filters_defined = len(custom_filter) # Find the length of the list to know how many filters were selected

        for query_filter in custom_filter:
            # Append the custom query filter to the query_target_filter which will be added to the URL
            query_target_filter += query_filter
            if not (count == filters_defined):
                # Means this iteration is not the last, therefore need to add a separator
                query_target_filter += "," # Used as a seperator in the URL
            count += 1
            if args.debug: print query_target_filter

        query_target_filter += query_target_filter_end
        my_url = base_url + sort_order + query_target_filter

    print("API Call to URL:")
    print(my_url + "\n")
    ret = session.get(my_url)
    response = ret.json()

    total_count = int(response['totalCount']) # Need to change to Int as returned in unicode
    imdata = response['imdata']

    aaaSessionLR = [] # Put into a list that will be printed by Tabulate

    if total_count == 0:
        print ("Query returned no results. Try modifying your filters\n")
    else:
        # There is at least 1 result
        for entry in imdata:
            # NOTE that the returned data is actually in Unicode format
            # Store each aaaSessionLR record into the list
            result = "Success"
            user = ""
            # Search for Internal Relationship Objects that the APIC Automatically creates/deletes
            # Hide these by default unless user wishes to see them as well
            if re.search("Failure", entry["aaaSessionLR"]["attributes"]["descr"]):
                result = "Failure"

            if entry["aaaSessionLR"]["attributes"]["user"] == "":
                # If APIC doesn't know the user, it returns a blank space, hence modifying to print UNKNOWN
                user = "UNKNOWN"
            else:
                # If user only wants to report on UNKNOWN attempts.
                # Since this else statement catches all other users
                # if option is enabled, skip it, otherwise record the entry
                if args.user == "UNKNOWN":
                    continue
                else:
                    user = entry["aaaSessionLR"]["attributes"]["user"]

            aaaSessionLR.append((entry["aaaSessionLR"]["attributes"]["created"],
                             entry["aaaSessionLR"]["attributes"]["id"], user,
                             entry["aaaSessionLR"]["attributes"]["trig"],
                             entry["aaaSessionLR"]["attributes"]["descr"], result))

        # Print out all the data collected, change the headers depending on the --internal flag
        print (tabulate(aaaSessionLR, headers = ["Timestamp", "ID", "User",
                                                 "Action", "Description", "Result"],
                        tablefmt="simple"))

        print ("=" * 80)
        print ("Total records returned: " + str(total_count))
        print ("=" * 80)

if __name__ == '__main__':
    main()
