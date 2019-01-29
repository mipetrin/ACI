#! /usr/bin/env python
"""
Simple script to allow user to review the changes taking place on their ACI Fabric

Requires the ACI Toolkit: pip install acitoolkit

To Do:
    * Once changes identified, push to:
        - Spark Room
        - Email
        - Whatever choice person wants. Part of a "Morning Coffee Report"
    * Doesn't take into consideration a large dataset. Assuming only wants night before. Otherwise results would
        exceed maximum and require pagination in the resulting dataset
    * Keep count of which user's are making the most changes
        - TopN users (in total)
        - TopN users (creation / deletion / modification)

Michael Petrinovic 2018
"""
import acitoolkit.acitoolkit as aci
from tabulate import tabulate
import datetime
import re


def main():
    description = ('Simple application that logs on to the APIC and displays the AAA logs')
    creds = aci.Credentials('apic', description)
    creds.add_argument('--start', help='Start Date/Time for the search until either --end date/time or current date/time. Full Format: 2018-02-23T08:14:25')
    creds.add_argument('--end', help='End Date/Time for the search until either --start date/time or the beginning of the records. Full Format: 2018-02-23T08:14:25')
    creds.add_argument('--user', help='Find records for this specific user. Default is all')
    creds.add_argument('--action', choices=["creation", "modification", "deletion"], help='Specify an action to filter on. Default is all')
    creds.add_argument('--sort', choices=["asc", "desc"], default="desc", help='Specify the sort order. Default is Descending. i.e. Newest logs at the top')
    creds.add_argument('--internal', action='store_true', help='Also show records for the Internal Relationship Objects')
    args = creds.get()

    # Login to APIC
    session = aci.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        exit(0)

    # ACI Query Target Filters:
    # https://www.cisco.com/c/en/us/td/docs/switches/datacenter/aci/apic/sw/2-x/rest_cfg/2_1_x/b_Cisco_APIC_REST_API_Configuration_Guide/b_Cisco_APIC_REST_API_Configuration_Guide_chapter_01.html

    base_url = '/api/node/class/aaaModLR.json?'

    # Sort by creation time. Either Ascending or Descending order
    sort_order = 'order-by=aaaModLR.created|%s' % (args.sort) # asc | desc

    # Build out the custom query-target-filter
    #if (args.start and args.end and args.user and args.action) is None:
    if not (args.start and args.end and args.user and args.action) is None:
        print "No custom filter selected"
        my_url = base_url + sort_order
    else:
        print "At least one custom filter is selected"
        query_target_filter = '&query-target-filter=and('

        custom_filter = []
        if not(args.start is None):
            # Meaning it is set
            custom_filter.append('gt(aaaModLR.created,"%s")' % (args.start))

        if not(args.end is None):
            # Meaning it is set
            custom_filter.append('lt(aaaModLR.created,"%s")' % (args.end))

        if not(args.user is None):
            # Meaning it is set
            custom_filter.append('wcard(aaaModLR.user, "%s")' % (args.user))

        if not(args.action is None):
            # Meaning it is set
            custom_filter.append('eq(aaaModLR.ind, "%s")' % (args.action))

        query_target_filter_end = ')'

        count = 1
        filters_defined = len(custom_filter) # Find the length of the list to know how many filters were selected

        for query_filter in custom_filter:
            # Append the custom query filter to the query_target_filter which will be added to the URL
            query_target_filter += query_filter
            if not (count == filters_defined):
                # Means this iteration is not the last, therefore need to add a separator
                query_target_filter += "," # Used as a seperator in the URL
            count += 1

        query_target_filter += query_target_filter_end
        my_url = base_url + sort_order + query_target_filter

    print("\nAPI Call to URL:")
    print(my_url + "\n")
    ret = session.get(my_url)
    response = ret.json()

    total_count = int(response['totalCount']) # Need to change to Int as returned in unicode
    imdata = response['imdata']
    internal_count = 0 #Keep track of the number of internal objects (Rs or Rt)

    aaaModLR = [] # Put into a list that will be printed by Tabulate
    users = {} # Dictionary to keep track of users and the type of aaaModLR (creation/deletion/modification)

    if total_count == 0:
        print ("Query returned no results. Try modifying your filters\n")
    else:
        # There is at least 1 result
        for entry in imdata:
            # NOTE that the returned data is actually in Unicode format
            # Store each aaaModLR record into the list
            internal_obj = False
            # Search for Internal Relationship Objects that the APIC Automatically creates/deletes
            # Hide these by default unless user wishes to see them as well
            if re.search("^R[s|t][A-Z]", entry["aaaModLR"]["attributes"]["descr"]):
                internal_obj = True
                #Count the number of internal objects
                internal_count += 1

            # Currently not taking into account the internal objects for user
            current_user = entry["aaaModLR"]["attributes"]["user"]
            current_action = entry["aaaModLR"]["attributes"]["ind"]

            if not current_user in users:
                #initialize the user and found action (creation/deletion/modification)
                users[current_user] = {current_action:1}
            else:
                if not current_action in users[current_user]:
                    #new action found (creation/deletion/modification)
                    users[current_user].update({current_action:1})
                else:
                    current_value = users[current_user][current_action]
                    users[current_user].update({current_action:current_value + 1})

            if args.internal:
                aaaModLR.append((entry["aaaModLR"]["attributes"]["created"],
                                 entry["aaaModLR"]["attributes"]["id"],
                                 entry["aaaModLR"]["attributes"]["user"],
                                 entry["aaaModLR"]["attributes"]["ind"],
                                 entry["aaaModLR"]["attributes"]["descr"],
                                 entry["aaaModLR"]["attributes"]["affected"], internal_obj))
            else:
                # deafult, hide internal objects
                if internal_obj:
                    continue
                else:
                    aaaModLR.append((entry["aaaModLR"]["attributes"]["created"],
                                     entry["aaaModLR"]["attributes"]["id"],
                                     entry["aaaModLR"]["attributes"]["user"],
                                     entry["aaaModLR"]["attributes"]["ind"],
                                     entry["aaaModLR"]["attributes"]["descr"],
                                     entry["aaaModLR"]["attributes"]["affected"]))

        # Print out all the data collected, change the headers depending on the --internal flag
        headers = []
        if args.internal:
            headers = ["Timestamp", "ID", "User", "Action", "Description",
                       "Affected Object", "Internal Relationship Object"]
        else:
            headers = ["Timestamp", "ID", "User", "Action", "Description", "Affected Object"]

        print (tabulate(aaaModLR, headers, tablefmt="simple"))

        print ("=" * 80)
        print ("Total Objects (inc. internal): " + str(total_count))
        if args.internal:
            print ("Total Objects (displayed): " + str(total_count))
        else:
            print ("Total Objects (displayed): " + str(total_count - internal_count))
        print ("=" * 80)

        #### Need to pretty this up
        #### TO DO: 
        for user_name, user_info in users.items():
            print ("User: ", str(user_name))

            for key in user_info:
                print (str(key) + ": ", str(user_info[key]))

if __name__ == '__main__':
    main()



'''
FROM MY TESTING. The list of URLs used for specific actions

    # action
    # &query-target-filter=and(or(eq(aaaModLR.ind, "modification")))

    # user
    # &query-target-filter=and(wcard(aaaModLR.user, "mike"))

    # start date == gt = greather than
    # &query-target-filter=and(gt(aaaModLR.created, "2018-02-24"))

    # end date == lt = less than
    # &query-target-filter=and(lt(aaaModLR.created, "2018-02-24"))

    # Start and End date
    # &query-target-filter=and(gt(aaaModLR.created,"%s"),lt(aaaModLR.created,"%s")' % (start_time, end_time)

    # user + start time/date + end time/date
    # &query-target-filter=and(gt(aaaModLR.created,"2018-02-23T08:00"),lt(aaaModLR.created,"2018-02-23T22:05"),wcard(aaaModLR.user, "mike"))

    # user + action
    # &query-target-filter=and(wcard(aaaModLR.user, "mike"),or(eq(aaaModLR.ind, "creation")))

    # user + action + start time/date   === for user + action + end time/date, just change the gt to lt
    # &query-target-filter=and(wcard(aaaModLR.user, "mike"),or(eq(aaaModLR.ind, "creation")),gt(aaaModLR.created, "2018-02-24"))

    # user + action + start time/date + end time/date
    # &query-target-filter=and(wcard(aaaModLR.user, "mike"),or(eq(aaaModLR.ind, "creation")),and(lt(aaaModLR.created, "2018-02-22"),gt(aaaModLR.created, "2018-02-20")))


Similarly, to capture via moquery natively on the CLI, for the all option (start date, end date AND specific user)

apic> moquery -c aaaModLR -x order-by="aaaModLR.created|desc" query-target-filter=and\(gt\(aaaModLR.created,\"2018-02-26\"\),lt\(aaaModLR.created,\"2018-02-28\"\),wcard\(aaaModLR.user,\"mipetrin\"\)\)
'''
