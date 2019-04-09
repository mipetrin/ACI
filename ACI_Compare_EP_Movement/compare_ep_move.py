#! /usr/bin/env python
"""
Script to execute both PRE and POST changes in a maintenance window to identify if any endpoints have changed

Requires the ACI Toolkit:

    pip install acitoolkit

Written by Michael Petrinovic 2019
"""

__version__ = 1.0


##############
# Imports
##############

import json
import time
import re
import os
import logging
import sys
from pprint import pprint
from tabulate import tabulate
from acitoolkit import Session, Credentials


##############
# Globals
##############

ep_tracker_dict = {} # Stores the raw raw fvCEp data that is read in from the pre/post JSON files
ep_tracker_diff = [] # Analyzed JSON fvCEp data, Endpoint is in both pre/post JSON files, but there is a difference
ep_only_in_pre_capture = [] # Analyzed JSON fvCEp data, Endpoint is in only PRE JSON files
ep_only_in_post_capture = [] # Analyzed JSON fvCEp data, Endpoint is in only POST JSON files
ep_summary = {"both":0, "pre":0, "post":0} # Store summary information. Code also adds per input file (pre/post) when created
ep_analysis_time = {} # Stores the analysis time when each JSON capture was created
ep_category_summary = {"tenant": {}, "app": {}, "epg": {}, "mac": {}, "encap": {}} # Stores total summary for each type
pre_suffix = "_PRE.json" # Output file suffix for the --pre capture
post_suffix = "_POST.json" # Output file suffix for the --post capture
detailed_summary = False # Enable detailed print out per --summary
detailed_summary_number = 1 # How many entries to check against (greater than or equal to) for above --summary output.
logging_filename = "" # Filename to be used if --log option used. Set during setup_logger()

# Create a custom logger
logger = logging.getLogger(__name__)
logger.propagate = False # Required to prevent the same logging message appearing twice


##############
# My Functions
##############

def setup_logger(logger, level, write_file):
    '''
    Set up my custom Logger
    '''
    # Create handlers
    logging_level = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warn": logging.WARNING,
        "critical": logging.CRITICAL,
    }.get(level, logging.DEBUG) # Although fallback is debug, actually argparse option sets default to info

    # Set logging level as specified on the command line via --debug
    logger.setLevel(logging_level)

    # Logger Formatting
    plain_formatter = "" # Basic Format to make use of Logger functionality but present it as normal "print" output on the console
    file_formatter = "%(asctime)s.%(msecs).03d || %(levelname)8s || "
    file_formatter += "(%(lineno)4d) || %(message)s"
    date_formatter = "%Z %Y-%m-%dT%H:%M:%S"

    # Console Logger
    logger_stdout_handler = logging.StreamHandler(sys.stdout)
    logger_stdout_handler.setFormatter(logging.Formatter(
        fmt=plain_formatter,
        datefmt=date_formatter)
    )
    logger.addHandler(logger_stdout_handler)

    # Check if --log specified on CLI to write logging output to a log file as well
    if write_file:
        full_script_name = os.path.basename(__file__)
        my_script_split = full_script_name.split(".py")
        script_name = my_script_split[0]

        # Get Time to save in the .log file.
        time_tuple = time.localtime() # get struct_time
        time_string = time.strftime("%d_%m_%Y_%H_%M_%S", time_tuple)

        # Setup filename for log file output. Eg: compare_ep_move_08_04_2019_22_24_22.log
        script_name_ext = "{}_{}.log".format(script_name, time_string)
        global logging_filename
        logging_filename = script_name_ext

        # Create File Handler
        logger_file_handler = logging.FileHandler(script_name_ext, mode='w') # Default option is mode='a' / append. =w overwrites
        logger_file_handler.setLevel(logging_level)

        # Create File Formatter and add it to handlers
        logger_file_handler.setFormatter(logging.Formatter(
            fmt=file_formatter,
            datefmt=date_formatter)
        )

        # Add handlers to the logger
        logger.addHandler(logger_file_handler)
        logger.info("Log file being written: {}".format(script_name_ext))
    else:
        logger.info("Log file NOT being written")


def print_header(text):
    '''
    Function to print a fancy header
    '''
    logger.info("\n")
    logger.info("#" * 80)
    logger.info(text)
    logger.info("#" * 80)


def raw_apic_query(session, class_url):
    '''
    Raw APIC Query and return a JSON object
    '''
    logger.info("Class URL is: {}\n".format(class_url))

    ret = session.get(class_url)
    response = ret.json()

    return response


def get_fvCEp(session, my_output_file, filter):
    '''
    Retrieve fvCEp from APIC and write to file
    '''
    class_url = '/api/node/class/fvCEp.json?rsp-subtree=full&rsp-subtree-class=fvCEp,fvRsCEpToPathEp'

    if filter == "None":
        my_url = class_url
    else:
        query_target_filter = '&query-target-filter=and(wcard(fvCEp.dn,"{}"))'.format(filter)
        my_url = class_url + query_target_filter

    query_response = raw_apic_query(session, my_url)

    # Save query_response to file
    write_to_file(query_response, my_output_file)

    logger.info("Total Endpoints Captured (fvCEp): {}\n".format(len(query_response["imdata"])))


def write_to_file(my_data, my_output_file):
    '''
    Function to save data to JSON file
    '''
    current_time = time.time()
    current_time = time.asctime(time.localtime(current_time))
    my_data["Analysis Time"] = current_time

    with open(my_output_file, 'w') as outfile:
        json.dump(my_data, outfile)

    logger.info("Output File Generated: {}\n".format(my_output_file))


def analyze_file(my_file, stage):
    '''
    Read JSON File, process it and store into a single Dictionary
    '''

    # Dictionary to maintain the fvCEp data
    global ep_tracker_dict
    global ep_analysis_time

    count = 0
    with open(my_file) as json_file:  
        data = json.load(json_file)

        # Update Analysis Time dictionary with info, to be printed during summary at end of script execution
        ep_analysis_time[stage] = data["Analysis Time"]

        # Loop through each entry of the query_response / JSON Dictionary in the file
        for entry in data["imdata"]:
            my_dn = str(entry["fvCEp"]["attributes"]['dn'])
            split_dn = my_dn.split("/")
            my_tenant = split_dn[1]
            my_app = split_dn[2]
            my_epg = split_dn[3]
            my_encap = str(entry["fvCEp"]["attributes"]['encap'])
            my_ip = str(entry["fvCEp"]["attributes"]['ip'])
            my_mac = str(entry["fvCEp"]["attributes"]['mac'])

            # Confirm if the fvCEp has a child object which should contain the fvRsCEpToPathEp Managed Object
            try:
                my_path = str(entry["fvCEp"]["children"][0]['fvRsCEpToPathEp']['attributes']['tDn'])
            except Exception as e:
                logger.warning("fvCEp with no Children objects. Skipping DN: {}\n".format(my_dn))
                continue

            # Node needs to consider vPC or Standard/Single Node
            if "protpaths" in my_path:
                # vPC path
                # Pod-1/Node-101-102
                my_node = str(re.search('pod-([0-9]+)/protpaths-([0-9]+)-([0-9]+)/', my_path).group(0))
            else:
                # Standard path
                # Pod-1/Node-101
                my_node = str(re.search('pod-([0-9]+)/paths-([0-9]+)/', my_path).group(0))

            # Interface needs to consider vPC or Single Interface
            # Eth1/32 or mipetrin-l3-vpc
            my_interface = str(re.search('\[.+\]', my_path).group(0))
            # Strip the [ ] from the result
            my_interface = my_interface[1:-1]

            # Confirm my collection is working as expected
            logger.debug('=' * 40)
            logger.debug('DN: ' + my_dn)
            logger.debug('Encap: ' + my_encap)
            logger.debug('IP: ' + my_ip)
            logger.debug('MAC: ' + my_mac)
            logger.debug('Tenant: ' + my_tenant)
            logger.debug('App: ' + my_app)
            logger.debug('EPG: ' + my_epg)
            logger.debug('Path: ' + my_path)
            logger.debug('Node: ' + my_node)
            logger.debug('Int: ' + my_interface)
            logger.debug('')

            count += 1 # Keep track of the number of Endpoints identified

            # Check if this is a new Endpoint or existing Endpoint
            if my_dn not in ep_tracker_dict:
                # New fvCEp so setup data structure
                ep_tracker_dict[my_dn] = {}
                ep_tracker_dict[my_dn]['mac'] = my_mac
                ep_tracker_dict[my_dn]['tenant'] = my_tenant
                ep_tracker_dict[my_dn]['app'] = my_app
                ep_tracker_dict[my_dn]['epg'] = my_epg
                ep_tracker_dict[my_dn][stage] = {}
            else:
                # Existing fvCEp so append to the stage (pre/post) structure
                ep_tracker_dict[my_dn][stage] = {}

            # Use a temporary dictionary to store info specific to the stage (eg: PRE/POST) which is then added to the parent dictionary
            tmp_dict = {}
            tmp_dict['ip'] = my_ip
            tmp_dict['encap'] = my_encap
            tmp_dict['path'] = my_path
            tmp_dict['node'] = my_node
            tmp_dict['interface'] = my_interface

            # Add back to the parent dictionary
            ep_tracker_dict[my_dn][stage] = tmp_dict

    logger.info("Length of {} is {} EP's".format(my_file, count))

    # Keep track globally to enable nice summary at the end
    tmp_file_name = stage + "_" + my_file
    ep_summary[tmp_file_name] = count


def compare_eps():
    '''
    Loop through ep_tracker_dict to identify what has changed (if anything)
        If Pod + Node / Interface / Encap is different = flag it

    After reading in JSON files via analyze_file(), ep_tracker_dict looks like the following

    'uni/tn-mipetrin/ap-mipetrin-vmm-ap/epg-vmm-102/cep-00:50:56:89:6C:03'
    {'app': 'ap-mipetrin-vmm-ap',
    'epg': 'epg-vmm-102',
    'mac': '00:50:56:89:6C:03',
    'post': {'encap': 'vlan-2621',
            'interface': 'eth1/32',
            'ip': '0.0.0.0',
            'node': 'pod-1/paths-102/',
            'path': 'topology/pod-1/paths-102/pathep-[eth1/32]'},
    'pre': {'encap': 'vlan-2621',
            'interface': 'eth1/32',
            'ip': '0.0.0.0',
            'node': 'pod-1/paths-102/',
            'path': 'topology/pod-1/paths-102/pathep-[eth1/32]'},
    'tenant': 'tn-mipetrin'}

    Then need to compare/anlyze the Endpoints and highlight differences
    '''
    # First compare if DN has both a "pre" and "post" otherwise flag it as only in one capture file
    # If fvCEp only has 1 entry, confirm if from PRE or POST and highlight as such (as something that has gone missing or something new attached?)
    for dn,endpoint in ep_tracker_dict.iteritems():
        # Confirm if exists in both PRE and POST
        if ("pre" in endpoint.keys()) and ("post" in endpoint.keys()):
            # Confirm if the Endpoint is the same (in both PRE/POST) when checking the Node / Interface / Encap
            try:
                if (endpoint["pre"]["interface"] != endpoint["post"]["interface"]) or (endpoint["pre"]["node"] != endpoint["post"]["node"]) or (endpoint["pre"]["encap"] != endpoint["post"]["encap"]):
                    # Means not the same, capture as different
                    logger.debug("")
                    logger.debug(dn)
                    logger.debug(endpoint["pre"]["node"])
                    logger.debug(endpoint["post"]["node"])
                    logger.debug(endpoint["pre"]["interface"])
                    logger.debug(endpoint["post"]["interface"])
                    logger.debug(endpoint["pre"]["encap"])
                    logger.debug(endpoint["post"]["encap"])

                    # Keep track globally to enable nice summary at the end of script execution
                    ep_summary["both"] += 1

                    # Add to tuple, with all the relevant data to be printed via Tabulate at end of script execution
                    ep_tracker_diff.append((endpoint["tenant"], endpoint["app"], endpoint["epg"], endpoint["mac"], "PRE", endpoint["pre"]["node"], endpoint["pre"]["interface"], endpoint["pre"]["encap"]))
                    ep_tracker_diff.append(("", "", "", "", "POST", endpoint["post"]["node"], endpoint["post"]["interface"], endpoint["post"]["encap"]))
                    ep_tracker_diff.append(("", "", "", "", "", "", "", ""))

                    # Global Category Tracking
                    if detailed_summary:
                        update_ep_category(endpoint["tenant"], endpoint["app"], endpoint["epg"], endpoint["mac"], endpoint["post"]["encap"])
            except Exception as e:
                logger.warning("Problem in 'BOTH' logic but only has PRE or POST. Skipping DN: {}\n".format(dn))
                continue
        elif "pre" in endpoint.keys():
            # Confirm Endpoint only exists in the "PRE" capture
            only_stage = "pre"

            # Keep track globally to enable nice summary at the end
            ep_summary["pre"] += 1

            logger.debug("Only in PRE: {}".format(dn))

            # Add to tuple, with all the relevant data to be printed via Tabulate at end of script execution
            ep_only_in_pre_capture.append((endpoint["tenant"], endpoint["app"], endpoint["epg"], endpoint["mac"], only_stage.upper(), endpoint[only_stage]["node"], endpoint[only_stage]["interface"], endpoint[only_stage]["encap"]))
            ep_only_in_pre_capture.append(("", "", "", "", "", "", "", ""))

            # Global Category Tracking
            if detailed_summary:
                update_ep_category(endpoint["tenant"], endpoint["app"], endpoint["epg"], endpoint["mac"], endpoint[only_stage]["encap"])
        elif "post" in endpoint.keys():
            # Confirm Endpoint only exists in the "POST" capture
            only_stage = "post"

            # Keep track globally to enable nice summary at the end
            ep_summary["post"] += 1

            logger.debug("Only in POST: {}".format(dn))

            # Add to tuple, with all the relevant data to be printed via Tabulate at end of script execution
            ep_only_in_post_capture.append((endpoint["tenant"], endpoint["app"], endpoint["epg"], endpoint["mac"], only_stage.upper(), endpoint[only_stage]["node"], endpoint[only_stage]["interface"], endpoint[only_stage]["encap"]))
            ep_only_in_post_capture.append(("", "", "", "", "", "", "", ""))

            # Global Category Tracking
            if detailed_summary:
                update_ep_category(endpoint["tenant"], endpoint["app"], endpoint["epg"], endpoint["mac"], endpoint[only_stage]["encap"])
        else:
            # Catch all, as does not match BOTH / PRE / POST
            logger.warning("ERROR with BOTH/PRE/POST Logic for DN: {}\n".format(dn))


def update_ep_category(my_tenant, my_app, my_epg, my_mac, my_encap):
    '''
    Function to keep total count for each category - if there is EP Movement (i.e. in BOTH / only PRE / only POST)

    Only called throughout code if --summary is used on the CLI
    '''
    # Confirm if particular item not already in the summary dictionary
    if my_tenant not in ep_category_summary["tenant"]:
        # Create the key and assign it value of 1
        ep_category_summary["tenant"][my_tenant] = 1
    else:
        # Otherwise, key already exists therefore increment count by 1
        ep_category_summary["tenant"][my_tenant] += 1

    # Below is identical code - as above with explanations. Only difference is what we check (App / EPG / MAC / Encap)
    if my_app not in ep_category_summary["app"]:
        ep_category_summary["app"][my_app] = 1
    else:
        ep_category_summary["app"][my_app] += 1

    if my_epg not in ep_category_summary["epg"]:
        ep_category_summary["epg"][my_epg] = 1
    else:
        ep_category_summary["epg"][my_epg] += 1

    if my_mac not in ep_category_summary["mac"]:
        ep_category_summary["mac"][my_mac] = 1
    else:
        ep_category_summary["mac"][my_mac] += 1

    if my_encap not in ep_category_summary["encap"]:
        ep_category_summary["encap"][my_encap] = 1
    else:
        ep_category_summary["encap"][my_encap] += 1


def get_raw_tenant_info(session):
    '''
    Function to obtain the raw list of Tenants / App Profiles / EPGs within the ACI Fabric. Is executed via the --list option

    Could then use any of those outputs with the --filter option
    '''
    class_url = '/api/node/class/fvAEPg.json'
    sort_order = '?order-by=fvAEPg.dn|%s' % ("asc") # asc | desc to determine ascending or descending order
    my_url = class_url + sort_order

    # Use API to obtain fvAEPg Managed Objects
    query_response = raw_apic_query(session, my_url)

    # Temporary List to store entries
    my_temp_data = []

    # Loop through each entry within the fvAEPg Managed Object outputs
    for epgs in query_response["imdata"]:
        my_dn = epgs["fvAEPg"]["attributes"]["dn"]
        split_dn = my_dn.split("/")
        my_tenant = split_dn[1]
        my_app = split_dn[2]
        my_epg = epgs["fvAEPg"]["attributes"]["name"]
        logger.debug("DN: {}".format(my_dn))

        my_temp_data.append((my_tenant, my_app, my_epg))

    # Add to tuple, with all the relevant data to be printed via Tabulate at end of script execution
    logger.info(tabulate(my_temp_data, headers = ["Tenant", "App Profile", "EPG"], tablefmt="grid"))
    logger.info("Total Objects: {}\n".format(len(query_response)))


def main():
    '''
    Main Function
    '''
    # Setup Arguments utilizing the ACIToolkit Credentials Method
    description = ('Help to determine EP movement during Maintenance Windows')
    creds = Credentials('apic', description)
    creds.add_argument('-v', '--version', action='version', version='%(prog)s == {}'.format(__version__))
    creds.add_argument("--debug", dest="debug", choices=["debug", "info", "warn", "critical"], default="info", help='Enable debugging output to screen')
    creds.add_argument('--log', action='store_true', help='Write the output to a log file: {}.log. Automatically adds timestamp to filename'.format(__file__.split(".py")[0]))
    creds.add_argument('--list', action='store_true', help='Print out the list of Tenants / App Profiles / EPGs available to work with')
    creds.add_argument('--filter', help='Specify what to filter on. Eg: "tn-mipetrin" or "ap-mipetrin-AppProfile". Use --list to identify what can be used for filtering. Default = None')
    creds.add_argument('--pre', help='Write the data to a file of your choosing. Specify your prefix. Format will be JSON and this extension is automatically added')
    creds.add_argument('--post', help='Write the data to a file of your choosing. Specify your prefix. Format will be JSON and this extension is automatically added')
    creds.add_argument('--compare', nargs=2, help='Compare the 2 files you specify. Be sure to pick a PRE and POST file')
    creds.add_argument('--summary', type=int, help='Optionally, print out detailed summary of identified Endpoints greater than x (provide totals per Tenant/App/EPG/MAC/Encap)')
    args = creds.get()

    # Set up custom logger
    setup_logger(logger, args.debug, args.log)

    # If --suumary enabled, set up globals to then utlize the additonal calculations throughout code
    if args.summary:
        global detailed_summary
        global detailed_summary_number
        detailed_summary = True
        detailed_summary_number = args.summary

    # Due to creds / argparse above, will always need to provide APIC / User / Pass even if wanting to do local comparison of PRE/POST JSON files
    # However, below check will ensure we actually only perform login if NOT doing a comparison. That is, if doing --compare, you can type ANY password even simply hitting enter
    if not args.compare:
        # Login to APIC only if NOT doing a comparison - as already have the data we need in the local JSON files
        session = Session(args.url, args.login, args.password)
        resp = session.login()

        # Check if the login was successful
        if not resp.ok:
            logger.critical('Could not login to APIC')
            my_error = resp.json()
            logger.critical("Specific Error: {}".format(my_error["imdata"][0]["error"]["attributes"]["text"]))
            exit(0)

    # Start time count at this point, otherwise takes into consideration the amount of time taken to input the password by the user
    start_time = time.time()
    logger.debug("Begin Execution of script")

    # Order of precedence is to execute list of tenants, pre capture, post capture, compare
    if args.list:
        print_header("Gathering available information from APIC...")
        get_raw_tenant_info(session)
    elif args.pre:
        print_header("Gathering 'PRE' Endpoints...")

        # Setup Filename for PRE file (using user input) and global pre_suffix
        my_filename_pre = args.pre + pre_suffix

        # Confirm if user has selected any --filter
        if args.filter:
            get_fvCEp(session, my_filename_pre, args.filter)
        else:
            get_fvCEp(session, my_filename_pre, "None")
    elif args.post:
        print_header("Gathering 'POST' Endpoints...")

        # Setup Filename for POST file (using user input) and global post_suffix
        my_filename_post = args.post + post_suffix

        # Confirm if user has selected any --filter
        if args.filter:
            get_fvCEp(session, my_filename_post, args.filter)
        else:
            get_fvCEp(session, my_filename_post, "None")
    elif args.compare:
        # Ensure *BOTH* the specified PRE and POST files exist. If not, throw error and explain which ones currently exist
        # Look for the suffix that I auto append during the --pre and --post file generation
        for file in args.compare:
            if pre_suffix in file:
                my_filename_pre = file
            elif post_suffix in file:
                my_filename_post = file
            else:
                logger.critical("Issue with file names supplied as don't contain the suffix defined. Are they the files generated by this script via the --pre / --post options?")
                exit(0)

        # Check that the files do in fact exist and are readable
        if not os.path.isfile(my_filename_pre):
            logger.critical("Need to ensure the PRE capture has been completed and readable")
            exit(0)

        # Check that the files do in fact exist and are readable
        if not os.path.isfile(my_filename_post):
            logger.critical("Need to ensure the POST capture has been completed and readable")
            exit(0)

        print_header("Analyzing 'PRE' Endpoints...")
        analyze_file(my_filename_pre, "pre")

        print_header("Analyzing 'POST' Endpoints...")
        analyze_file(my_filename_post, "post")

        print_header("Comparing 'PRE' and 'POST' Endpoints...")
        compare_eps()

        print_header("Endpoints with Movements...")
        logger.info("\n" + tabulate(ep_tracker_diff, headers = ["Tenant", "App Profile", "EPG", "MAC", "Stage", "Node", "Interface", "Encap"], tablefmt="grid"))

        print_header("Endpoints only in PRE capture")
        logger.info("\n" + tabulate(ep_only_in_pre_capture, headers = ["Tenant", "App Profile", "EPG", "MAC", "Stage", "Node", "Interface", "Encap"], tablefmt="grid"))

        print_header("Endpoints only in POST capture")
        logger.info("\n" + tabulate(ep_only_in_post_capture, headers = ["Tenant", "App Profile", "EPG", "MAC", "Stage", "Node", "Interface", "Encap"], tablefmt="grid"))

        # Check if the --summary option is enabled
        if detailed_summary:
            print_header("(Moved/PRE/POST) Category entries that have a total greater than: {}".format(detailed_summary_number))

            logger.debug(ep_category_summary)
            ep_summary_data = "" # String object to print out detailed summary that will be built using code below

            # Loop through EP Categories to then be stored in the string object "ep_summary_data"
            for category,entries in ep_category_summary.iteritems():
                ep_summary_data += "\n" + category.upper() + "\n"

                # Then loop through each item within each category to highlight the particular Tenant/App/EPG/MAC/Encap
                for item,number in entries.iteritems():
                    # Check if the current entry has a value greater than or equal to the value specified on the CLI
                    if number >= detailed_summary_number:
                        ep_summary_data += "{:6} == {}\n".format(number, item)

            # Also provide a tally of the total amount of EPs that are in BOTH / PRE / POST - as identified
            grand_total_eps = ep_summary["both"] + ep_summary["pre"] + ep_summary["post"]
            ep_summary_data += "\nGRAND TOTAL\n"
            ep_summary_data += "{:6} EPs across all captures\n".format(grand_total_eps)
            logger.info(ep_summary_data) # Print out the data

        print_header("Summary")
        # Structure of ep_summary{'pre': 11, 'post': 15, 'compare_ep_move_PRE.json': 11, 'compare_ep_move_POST.json': 15}
        for key, value in sorted(ep_summary.iteritems(), reverse=True):
            # Loop through dictionary and find if they are the .JSON filenames
            if "json" in key:
                if "pre" in key:
                    # Check for _PRE
                    logger.info("PRE Filename: {}".format(key))
                    logger.info("   Endpoints read: {}".format(value))
                    logger.info("   Captured on: {}\n".format(ep_analysis_time["pre"]))
                elif "post" in key:
                    # Check for _POST
                    logger.info("POST Filename: {}".format(key))
                    logger.info("   Endpoints read: {}".format(value))
                    logger.info("   Captured on: {}\n".format(ep_analysis_time["post"]))
                else:
                    logger.warning("ERROR with determiniation of PRE/POST filename in ep_summary")

        # Print out analysis
        logger.info("Endpoints with movement: {}".format(ep_summary["both"]))
        logger.info("Endpoints only in PRE: {}".format(ep_summary["pre"]))
        logger.info("Endpoints only in POST: {}\n".format(ep_summary["post"]))

        if args.log:
            logger.info("Log file written: {}\n".format(logging_filename))
    else:
        logger.critical("\nSomething wrong with your selections. Please try again or use the --help option\n")
        creds.print_help()

    finish_time = time.time() # Calculate finish time

    logger.info("#" * 80)
    logger.info("Started analysis @ {}".format(time.asctime(time.localtime(start_time))))
    logger.info("Ended analysis @ {}".format(time.asctime(time.localtime(finish_time))))
    logger.info("--- Total Execution Time: %s seconds ---" % (finish_time - start_time))
    logger.info("#" * 80)


if __name__ == '__main__':
    main()
