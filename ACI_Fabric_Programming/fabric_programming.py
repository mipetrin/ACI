#! /usr/bin/env python
"""
Script to check for various types of issues that may be occurring within an ACI Environment.

Requires the ACI Toolkit:

    pip install acitoolkit


To Do:
======
* Clean up all the output that is being printed to screen. Make it easier to read

* Output
    * Identify which NODE/s are impacted
    * Identify which Object/s are mismatched
    * Create a summary table on a per node basis, which then runs through each check and gives output?

* Filter
    * Allow a nodeID filter to be used, to verify all checks just for that Node?
    * Put a filter to only perform one check at a time? Or provide options to do 1/2/3/all
    * Put a filter on a NODE basis
    * Put a filter on a Pod basis
    * Put a filter to check on a per tenant basis?

* Misc
    * Do I need any special considerations for L2 / L3 outs / L4-7 devices?
    * Store it in a Docker Container and ensure has acitoolkit installed?



if logger.isEnabledFor(logging.DEBUG):

how to handle logger.info and pprint ?

from pprint import pformat
ds = [{'hello': 'there'}]
logging.debug(pformat(ds))


Written by Michael Petrinovic 2018
"""
__version__ = 1.0

################
# Module Imports
################

import time
import sys
import json
import re
import os
import logging
from pprint import pprint
from pprint import pformat
from collections import OrderedDict
from tabulate import tabulate
from acitoolkit import Session, Credentials, Node, ExternalSwitch, Tenant, Context, ConcreteEp


###########
# Variables
###########

debug = False
instance = 0
global_vlanCktEp = []
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

    # Used to set Global variable, so can also perform selective conditional loops only IF debug option is selected
    if level == "debug":
        global debug
        debug = True

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


def print_checks_available():
    '''
    Function to explain the checks that can be performed
    '''
    # Ordered Dictionary so will always be printed out in the following order
    checks_available = OrderedDict()
    checks_available["EPG_VXLAN_ENCAP"] = "Identify if the EPG (VXLAN encap) is consistent across the Fabric"
    checks_available["BD_VXLAN_ENCAP"] = "Identify if the BD (VXLAN encap) is consistent across the Fabric"
    checks_available["VZANY_MISSING"] = "Identify if the vzAny contract is missing from a Tenant/VRF across the Fabric"
    checks_available["EPG_ENCAP_MISSING"] = "Identify if the EPG (VLAN Encap) is missing from any nodes across the Fabric"
    checks_available["EPG_BD_MAPPING"] = "Identify if the EPG to BD mapping is correct when comparing GUI output and node programming across the Fabric"
    checks_available["ALL"] = "Run all available tests"

    msg = "Current Checks Available to test"

    print_header(msg)
    tmp_string = "\n{:<20} {:<100}".format('Test','Description')
    logger.info(tmp_string)
    logger.info("-" * len(msg))
    for test,desc in checks_available.iteritems():
        tmp_string = "{:<20} {:<100}".format(test, desc)
        logger.info(tmp_string)


def raw_apic_query(session, class_url):
    '''
    Raw APIC Query and return a JSON object
    '''
    logger.debug("\n%% class_url is: {}\n".format(class_url))
    ret = session.get(class_url)
    response = ret.json()
    imdata = response['imdata']
    return imdata


def get_tenant_context(session):
    '''
    Return the list of Tenants available, along with their VRFs + ScopeID
    '''
    tenant_data = []
    tmp_dict = {}
    tenants = Tenant.get(session)

    for tenant in tenants:
        contexts = Context.get(session, tenant)
        for context in contexts:
            #tmp_dict = {}
            tmp_dict[context.scope] = {"name":tenant.name, "vrf":context.name}
            tenant_data.append(tmp_dict)

    return tmp_dict


def get_vlanCktEp(session):
    '''
    Multiple checks require the output of vlanCktEp in JSON. Instead of each function making the API call,
    optimized so that only the first function makes the API call and then all subsequent calls uses the locally stored copy
    '''
    global instance
    global global_vlanCktEp

    if instance == 0:
        class_url = '/api/node/class/vlanCktEp.json?query-target=self'
        global_vlanCktEp = raw_apic_query(session, class_url)
        instance = 1
        logger.debug("%%%% FIRST REQUST for vlanCktEp. Making API call")
        return global_vlanCktEp
    else:
        # Already performed API pull, simply return the global
        logger.debug("%%%% NO FURTHER NEED for API call for vlanCktEp. Returning previous object")
        return global_vlanCktEp


def EPG_VXLAN_ENCAP(session):
    '''
    Identify if the EPG (VXLAN encap) is consistent across Fabric
    '''

    #class_url = '/api/node/class/vlanCktEp.json?query-target=self'
    #query_response = raw_apic_query(session, class_url)
    query_response = get_vlanCktEp(session)
    '''
    # Relevant pieces of information that I want to pull or use
    {
        u 'vlanCktEp': {
            u 'attributes': {
                u 'dn': u 'topology/pod-1/node-102/sys/ctx-[vxlan-2293768]/bd-[vxlan-16580493]/vlan-[vlan-1302]',
                u 'encap': u 'vlan-1302',
                u 'epgDn': u 'uni/tn-mipetrin/ap-TEST/epg-EPG-Web',
                u 'fabEncap': u 'vxlan-9693',
                u 'name': u 'mipetrin:TEST:EPG-Web'
            }
        }
    }
    '''

    # Dictionary to maintain the EPG Encaps
    epg_encap_dict = {}

    # Loop over each Concrete object - vlanCktEp - which is the VLANs deployed on each switch
    # Extract the necessary information
    for vlanCktEp in query_response:
        epg_dn = vlanCktEp["vlanCktEp"]["attributes"]["epgDn"]
        accessEncap = vlanCktEp["vlanCktEp"]["attributes"]["encap"]
        fabEncap = vlanCktEp["vlanCktEp"]["attributes"]["fabEncap"]
        node = re.search('node-([0-9]+)/', vlanCktEp["vlanCktEp"]["attributes"]["dn"]).group(1)

        if epg_dn not in epg_encap_dict:
            epg_encap_dict[epg_dn] = {}

        if accessEncap not in epg_encap_dict[epg_dn]:
            epg_encap_dict[epg_dn][accessEncap] = []

        encapDict_Tmp = {}
        encapDict_Tmp['node'] = node
        encapDict_Tmp['fabEncap'] = fabEncap
        epg_encap_dict[epg_dn][accessEncap].append(encapDict_Tmp)

    # Confirm if debug option selected - through global variable set during setup_logger
    if debug:
        logger.debug("/" * 80)

        for epg,encap_nodes in epg_encap_dict.iteritems():
            logger.debug("EPG: {}".format(epg))
            logger.debug("Encap Nodes: {}".format(encap_nodes))
        logger.debug("/" * 80)

    logger.debug("#" * 80)
    logger.debug("Length of returned object: {}".format(len(query_response)))
    logger.debug("#" * 80)


    result = []

    for epg, encap_nodes in epg_encap_dict.iteritems():
        for vlanKey, vlan in encap_nodes.iteritems():
            fabEncapTemp=""
            for deployment in vlan:
                if fabEncapTemp == "" or deployment["fabEncap"] == fabEncapTemp:
                    fabEncapTemp = deployment["fabEncap"]
                else: # something is wrong
                    tmpDict = {}
                    tmpDict["epgDn"] = epg
                    tmpDict["epgDeployment"] = encap_nodes
                    if tmpDict not in result:    # some epg has more than one access encap.
                        result.append(tmpDict)
                    break
    if len(result) == 0:
        logger.info("\nNo issue found with each EPG VXLAN ENCAP across the fabric matching as expected\n")
    else:
        logger.debug(result)
        vxlan_vnid_counter = 0
        for item in result:
            logger.info("epgDn: " + item["epgDn"])
            tmp_vnids = {}
            for key, nodeFabEncaps in item["epgDeployment"].iteritems():
                logger.info("++ " + key )
                for nodeFabEncap in nodeFabEncaps:
                    logger.debug("---- " + 'node ' +  nodeFabEncap['node'] + " : " + nodeFabEncap['fabEncap'])
                    if nodeFabEncap['fabEncap'] not in tmp_vnids:
                        tmp_vnids[str(nodeFabEncap['fabEncap'])] = []
                        tmp_vnids[str(nodeFabEncap['fabEncap'])].append(str(nodeFabEncap['node']))
                    else:#
                        tmp_vnids[str(nodeFabEncap['fabEncap'])].append(str(nodeFabEncap['node']))
                for vxlan, node_ids in tmp_vnids.iteritems():
                    logger.info("---- {}, Node IDs: {}".format(vxlan, sorted(node_ids)))
                    vxlan_vnid_counter += 1
            logger.info("\n")
        logger.info("'{}' EPGs found to have issues, across {} VXLAN VNIDs".format(len(result), vxlan_vnid_counter))


def BD_VXLAN_ENCAP(session):
    '''
    Identify if the BD (VXLAN encap) is consistent across the Fabric (similar to check EPG_VXLAN_ENCAP but at BD level instead of EPG)

    1. Pull vlanCktEp and look at the DN for each deployed VLAN. 
        u 'dn': u 'topology/pod-1/node-102/sys/ctx-[vxlan-2293768]/bd-[vxlan-16580493]/vlan-[vlan-1302]',

    2. From this take note of the Node / VLAN <--> BD VXLAN mapping
    '''
    #class_url = '/api/node/class/vlanCktEp.json?query-target=self'
    #query_response = raw_apic_query(session, class_url)
    query_response = get_vlanCktEp(session)

    '''
    # Relevant pieces of information that I want to pull or use
    {
        u 'vlanCktEp': {
            u 'attributes': {
                u 'dn': u 'topology/pod-1/node-102/sys/ctx-[vxlan-2293768]/bd-[vxlan-16580493]/vlan-[vlan-1302]',
                u 'encap': u 'vlan-1302',
                u 'epgDn': u 'uni/tn-mipetrin/ap-TEST/epg-EPG-Web',
                u 'name': u 'mipetrin:TEST:EPG-Web'
            }
        }
    }
    '''

    # Dictionary to maintain the EPG Encaps
    bd_encap_dict = {}

    # Loop over each Concrete object - vlanCktEp - which is the VLANs deployed on each switch
    # Extract the necessary information
    for vlanCktEp in query_response:
        epg_dn = vlanCktEp["vlanCktEp"]["attributes"]["epgDn"]
        access_encap = vlanCktEp["vlanCktEp"]["attributes"]["encap"]
        #fabEncap = vlanCktEp["vlanCktEp"]["attributes"]["fabEncap"]
        node = re.search('node-([0-9]+)/', vlanCktEp["vlanCktEp"]["attributes"]["dn"]).group(1)
        bd_vxlan = re.search('bd-\[vxlan-([0-9]+)]/', vlanCktEp["vlanCktEp"]["attributes"]["dn"]).group(1)
        object_dn = vlanCktEp["vlanCktEp"]["attributes"]["dn"]

        if epg_dn not in bd_encap_dict:
            bd_encap_dict[epg_dn] = {}

        if access_encap not in bd_encap_dict[epg_dn]:
            bd_encap_dict[epg_dn][access_encap] = []

        encapDict_Tmp = {}
        encapDict_Tmp['node'] = node
        encapDict_Tmp['bd_vxlan'] = bd_vxlan
        bd_encap_dict[epg_dn][access_encap].append(encapDict_Tmp)

    # Confirm if debug option selected - through global variable set during setup_logger
    if debug:
        logger.debug("/" * 80)

        for epg,encap_nodes in bd_encap_dict.iteritems():
            logger.debug("EPG: {}".format(epg))
            logger.debug("Encap Nodes: {}".format(encap_nodes))
        logger.debug("/" * 80)

    # Once printed, then check if ANY of the BD_VXLAN SegIDs are different across the Fabric for the associated EPG / Node pairings
    result = []
    for epg, encap_nodes in bd_encap_dict.iteritems():
        for vlanKey, vlan in encap_nodes.iteritems():
            bd_fabEncap_temp=""
            for deployment in vlan:
                if bd_fabEncap_temp == "" or deployment["bd_vxlan"] == bd_fabEncap_temp:
                    bd_fabEncap_temp = deployment["bd_vxlan"]
                else: # something is wrong
                    tmpDict = {}
                    tmpDict["epgDn"] = epg
                    tmpDict["epgDeployment"] = encap_nodes
                    if tmpDict not in result:    # some epg has more than one access encap.
                        result.append(tmpDict)
                    break
    if len(result) == 0:
        logger.info("\nNo issue found with each BD VXLAN ENCAP across the fabric matching as expected\n")
    else:
        vxlan_vnid_counter = 0
        for item in result:
            logger.info("epgDn: " + item["epgDn"])
            tmp_vnids = {}
            for key, nodeFabEncaps in item["epgDeployment"].iteritems():
                logger.info("++ " + key )
                for nodeFabEncap in nodeFabEncaps:
                    logger.debug("---- " + 'node ' +  nodeFabEncap['node'] + " : " + nodeFabEncap['bd_vxlan'])
                    if nodeFabEncap['bd_vxlan'] not in tmp_vnids:
                        tmp_vnids[str(nodeFabEncap['bd_vxlan'])] = []
                        tmp_vnids[str(nodeFabEncap['bd_vxlan'])].append(str(nodeFabEncap['node']))
                    else:
                        tmp_vnids[str(nodeFabEncap['bd_vxlan'])].append(str(nodeFabEncap['node']))
                for vxlan, node_ids in tmp_vnids.iteritems():
                    logger.info("---- {}, Node IDs: {}".format(vxlan, sorted(node_ids)))
                    vxlan_vnid_counter += 1
            logger.info("\n")
        logger.info("'{}' EPGs found to have issues, across {} VXLAN VNIDs".format(len(result), vxlan_vnid_counter))


def VZANY_MISSING(session):
    '''
    Identify if the vzAny contract is missing from a Tenant/VRF across the Fabric

    Premise:
        * Obtain all of the Tenants / VRFs / ScopeID (per VRF) and store in a dictionary. eg: "all_tenants"
        * Obtain all of the contracts deployed across the Fabric (actrlRule)
        * Loop through all of the contracts, searching for instances of "any_any_any" and permit action
        * Once found, identify which Tenant/VRF this belongs to
            * Store in another dictionary/list - eg: found_tenants
        * Once gone through all contracts, compare what Tenant/VRFs are in the "found_tenants" dictionary with the original "all_tenants" data
            * If were to remove all instances of "found_tenants" from "all_tenants"
                what is remaining should be all the ones without the specific contract deployed

    # TO DO:
    # Even if correclty outputs, say 10 actrlRules on deployed leaf nodes, is 10 out 84 correct, or should be 20/30/etc.
        Similar to fvLocale for contracts
    '''
    # All contracts deployed across the ACI Fabric
    class_url_all_contracts = '/api/node/class/actrlRule.json?query-target=self'
    query_response_all_contracts = raw_apic_query(session, class_url_all_contracts)

    # Contract Type that we plan to search for across the fabric
    contract_search_type = "any_any_any"

    # Specific contracts deployed across the ACI Fabric that match above variable: contract_search_type
    class_url = '/api/node/class/actrlRule.json?query-target-filter=and(eq(actrlRule.prio,"{}"))'.format(contract_search_type)
    query_response_specific_contracts = raw_apic_query(session, class_url)
    #print ("#" * 80)
    logger.info("#" * 80)
    tenant_info = get_tenant_context(session) ## original
    '''
    tenant_info
    {
        '2916355': {
            'name': 'mipetrin',
            'vrf': 'mipetrin-vmm-vrf'
        }
    }
    '''
    tenants_with_deployed_default_contracts = {}
    stale_vrf_node_dict = {}
    unenforced_vrfs = []
    unenforced_vrfs_scope = []
    permit_counter = 0

    for deployed_contract in query_response_specific_contracts:
        # Double confirm that the returned object via API call does ONLY contain the "any_any_any" contracts
        # Searching for any_any_any contract with permit action
        fltId = str(deployed_contract["actrlRule"]["attributes"]["fltId"])
        sPcTag = str(deployed_contract["actrlRule"]["attributes"]["sPcTag"])
        dPcTag = str(deployed_contract["actrlRule"]["attributes"]["dPcTag"])
        prio = str(deployed_contract["actrlRule"]["attributes"]["prio"])
        action = str(deployed_contract["actrlRule"]["attributes"]["action"])
        scopeId = str(deployed_contract["actrlRule"]["attributes"]["scopeId"])
        cur_dn = str(deployed_contract["actrlRule"]["attributes"]["dn"])
        # Take note of which scope / vrf / tenant
        # What happens if the cur_scope is present in H/W but not matching a Tenant/VRF
        # Will lead to failure in below code. Need to test for this scenario
        try:
            cur_tenant = str(tenant_info[scopeId]["name"])
            cur_context = str(tenant_info[scopeId]["vrf"])
        except:
            # Likely means a stale hardware entry as pointing to a ScopeID that doesn't actually exist
            stale_vrf_node = str(re.search('node-([0-9]+)/', cur_dn).group(1))

            # Check if we have seen this invalid scope previously
            if scopeId not in stale_vrf_node_dict:
                stale_vrf_node_dict[scopeId] = []

            # Eg: stale_vrf_node_dict = {"1234567":[101,102,103]}
            # Add this current node to the list that is paired to the Key - ScopeId
            stale_vrf_node_dict[scopeId].append(stale_vrf_node)
            if debug:
                #print ("Found issue with the VRF ScopeID {} for Rule {}".format(scopeId, cur_dn))
                #print ("Likely stale H/W entry on Node {}. Can double check if VRF exists via: apic# moquery -c fvCtx -f 'fv.Ctx.scope==\"{}\"'".format(stale_vrf_node, scopeId))
                #print ("#" * 25)
                logger.debug("Found issue with the VRF ScopeID {} for Rule {}".format(scopeId, cur_dn))
                logger.debug("Likely stale H/W entry on Node {}. Can double check if VRF exists via: apic# moquery -c fvCtx -f 'fv.Ctx.scope==\"{}\"'".format(stale_vrf_node, scopeId))
                logger.debug("#" * 25)
            continue

        if prio == contract_search_type and action == "permit" and sPcTag == "any" and dPcTag == "any":
            if fltId == "default":
                # TESTING
                # print ("Found a default")
                # print (fltId)
                # print (sPcTag)
                # print (dPcTag)
                # print (cur_dn)
                # TESTING
                permit_counter += 1

                # Check if already doesn't exist within larger Dictionary. otherwise add new
                if scopeId not in tenants_with_deployed_default_contracts:
                    tmp = []
                    tenants_with_deployed_default_contracts[scopeId] = {"name":cur_tenant, "vrf":cur_context, "nodes":tmp}
                    tenants_with_deployed_default_contracts[scopeId]["nodes"].append(cur_dn)
                else:
                    # Current Scope already exists, since scope is unique to tenant/context, should just update the nodes list
                    tenants_with_deployed_default_contracts[scopeId]["nodes"].append(cur_dn)

            elif fltId == "implicit":
                #print ("Found implicit, likely unenforced VRF")
                logger.debug("Found implicit, likely unenforced VRF")
                # Look to add to a seperate dictionary, to then print out as unenforced VRFs
                if scopeId not in unenforced_vrfs_scope:
                    unenforced_vrfs.append((cur_tenant, cur_context, scopeId))
                    unenforced_vrfs_scope.append(scopeId)
                    #print (unenforced_vrfs)
                    #print (unenforced_vrfs_scope)
            else:
                #print ("Something went wrong with {}".format(cur_dn))
                logger.info("Something went wrong with {}".format(cur_dn))
                # Likely the last option, which is implarp

    # Obtain all VRFs that should be deployed across the Fabric and on which nodes
    class_url_l3Ctx = '/api/node/class/l3Ctx.json?query-target=self'
    query_response_l3Ctx = raw_apic_query(session, class_url_l3Ctx)
    unenforced_vrf_count = 0
    l3Ctx_nodes_dict = {}

    for deployed_vrf in query_response_l3Ctx:
        ctxEncap = str(deployed_vrf["l3Ctx"]["attributes"]["encap"])
        ctxPKey = str(deployed_vrf["l3Ctx"]["attributes"]["ctxPKey"])
        ctxDn = str(deployed_vrf["l3Ctx"]["attributes"]["dn"])
        ctxName = str(deployed_vrf["l3Ctx"]["attributes"]["name"]) # --> seen this as null/empty if on Spine. eg: black-hole VRF
        ctxEnforce = str(deployed_vrf["l3Ctx"]["attributes"]["pcEnfPref"])
        ctxScope = str(deployed_vrf["l3Ctx"]["attributes"]["scope"])
        ctxNode = str(re.search('node-([0-9]+)/', ctxDn).group(1))
        #print (ctxDn)
        #print (ctxName)
        #print (ctxEncap)
        #print (ctxPKey)
        #print (ctxEnforce)
        #print (ctxNode)
        #print (ctxScope)
        logger.debug(ctxDn)
        logger.debug(ctxName)
        logger.debug(ctxEncap)
        logger.debug(ctxPKey)
        logger.debug(ctxEnforce)
        logger.debug(ctxNode)
        logger.debug(ctxScope)
        logger.debug("*" * 40)
        if ctxEnforce == "unenforced":
            vxlan_vnid = str(re.search('vxlan-([0-9]+)$', ctxEncap).group(1))
            #print vxlan_vnid
            logger.debug(vxlan_vnid)
            if vxlan_vnid in unenforced_vrfs_scope:
                #print True
                unenforced_vrf_count += 1

        if ctxScope not in l3Ctx_nodes_dict:
            l3Ctx_nodes_dict[ctxScope] = []

        l3Ctx_nodes_dict[ctxScope].append(ctxNode)

    #pprint(tenants_with_deployed_default_contracts)
    #pprint(l3Ctx_nodes_dict)
    same_nodes_counter = 0
    different_nodes_counter = 0
    no_nodes_counter = 0
    for item_scope, item_nodes in l3Ctx_nodes_dict.iteritems():
        # Need to test if it is actually in both dictionaries otherwise will throw error
        if item_scope in tenants_with_deployed_default_contracts:
            # If in the tenants_with_deployed_default_contracts, this is a dict, so need to look into NAME/NODES/VRF
            # also need to re.search through the NODES to get the correct matches possible
            #name{}, vrf{}, nodes = []
            deployed_node_ids = []
            actrl_name = tenants_with_deployed_default_contracts[item_scope]["name"]
            actrl_vrf = tenants_with_deployed_default_contracts[item_scope]["vrf"]
            actrl_nodes = tenants_with_deployed_default_contracts[item_scope]["nodes"]
            for actrl_node_id in actrl_nodes:
                tmp_node = str(re.search('node-([0-9]+)/', actrl_node_id).group(1))
                deployed_node_ids.append(tmp_node)

            #if sorted(item_nodes) == sorted(tenants_with_deployed_default_contracts[item_scope]):
            if sorted(item_nodes) == sorted(deployed_node_ids):
                #print ("Node IDs match in both dictionaries for EPG {}".format(item_scope))
                #print ("#" * 25)
                logger.debug("Node IDs match in both dictionaries for EPG {}".format(item_scope))
                logger.debug("#" * 25)
                same_nodes_counter += 1
            else:
                #print ("Node ID mis-match for Default Contract for VRF {} (Scope {}) in Tenant {}".format(actrl_vrf, item_scope, actrl_name))
                #print ("   Expected: {}".format(sorted(item_nodes)))
                #print ("     Actual: {}".format(sorted(deployed_node_ids)))
                #print ("       Diff: {}".format(sorted(list_diff(sorted(item_nodes), sorted(deployed_node_ids)))))
                #print ("#" * 25)
                logger.info("Node ID mis-match for Default Contract for VRF {} (Scope {}) in Tenant {}".format(actrl_vrf, item_scope, actrl_name))
                logger.info("   Expected: {}".format(sorted(item_nodes)))
                logger.info("     Actual: {}".format(sorted(deployed_node_ids)))
                logger.info("       Diff: {}".format(sorted(list_diff(sorted(item_nodes), sorted(deployed_node_ids)))))
                logger.info("#" * 25)
                different_nodes_counter += 1
        else:
            # This VRF/Scope does NOT have a default contract but the VRF is deployed on various Nodes
            # Doesn't mean it is a problem, could just be the configuration of the VRF
            #print ("No default contract found for VRF Scope: {}".format(item_scope))
            #print ("   VRF is deployed on Nodes: {}".format(sorted(item_nodes)))
            #print ("#" * 25)
            logger.debug("No default contract found for VRF Scope: {}".format(item_scope))
            logger.debug("   VRF is deployed on Nodes: {}".format(sorted(item_nodes)))
            logger.debug("#" * 25)
            no_nodes_counter += 1

    apic_vrf_not_deployed = 0
    apic_vrf_not_deployed_list = [] # Contain Tenant/Context/ScopeId
    apic_vrf_not_deployed_scope_list = [] # Only contain ScopeID
    for apic_config_vrf_scope, apic_config_vrf_details in tenant_info.iteritems():

        if apic_config_vrf_scope not in l3Ctx_nodes_dict:
            # Means we have a VRF that is configured on APIC but not deployed on ANY node
            # Could be by design, not complete configuration, or an issue
            # Possibly flag for further investigation?
            vrf_name = apic_config_vrf_details["vrf"]
            vrf_scope = apic_config_vrf_scope
            vrf_tenant = apic_config_vrf_details["name"]
            #print ("VRF {} (Scope ID {}) in Tenant {} is not deployed anywhere".format(vrf_name, vrf_scope, vrf_tenant))
            logger.debug("VRF {} (Scope ID {}) in Tenant {} is not deployed anywhere".format(vrf_name, vrf_scope, vrf_tenant))
            apic_vrf_not_deployed_list.append((vrf_tenant, vrf_name, vrf_scope))
            apic_vrf_not_deployed_scope_list.append(vrf_scope)
            apic_vrf_not_deployed += 1

    # TO DO: PERHAPS TURN THE BELOW INTO A DEBUG ITEM
    logger.debug("#" * 80)
    logger.debug(("Deployed '{}' contracts across the entire Fabric").format(contract_search_type))
    logger.debug("")
    if debug:
        if len(tenants_with_deployed_default_contracts) != 0:
            #pprint (tenants_with_deployed_default_contracts)
            logging.debug("\n" + pformat(tenants_with_deployed_default_contracts, indent=4))
        else:
            logger.debug("Zero (0) contracts found")
    logger.debug("#" * 80)

    possibly_missing_contract = []
    #print apic_vrf_not_deployed_scope_list
    for scopeId, tenant_vrf in tenant_info.iteritems():
        #print (tenant_vrf)
        if scopeId not in tenants_with_deployed_default_contracts and scopeId not in unenforced_vrfs_scope and scopeId not in apic_vrf_not_deployed_scope_list:
            # Found a tenant / context possible missing a "any_any_any" contract rule
            logger.debug("(ScopeID: {})  Tenant Name: {}  ==  VRF Name: {}".format(scopeId, tenant_vrf["name"], tenant_vrf["vrf"]))
            possibly_missing_contract.append((tenant_vrf["name"], tenant_vrf["vrf"], scopeId))
            #missing_counter += 1

    ### Print out invalid VRFs and the Nodes found on
    logger.info("Found issues with the following Scope IDs on the following Nodes")
    logger.info("Likely stale H/W entry on each Node identified.\n")
    for scopeId_key, node_values in stale_vrf_node_dict.iteritems():
        # Print each one out
        logger.info("++ " + scopeId_key)
        logger.info("---- Node IDs: {}".format(sorted(node_values)))
        logger.info("Verify with apic# moquery -c fvCtx -f 'fv.Ctx.scope==\"{}\"'\n".format(scopeId_key))

    logger.info("#" * 80)

    logger.info("Tenants/VRFs that are configured on the APIC but are NOT deployed on any node (could be by design). Double check:".format(contract_search_type))
    logger.info("")
    logger.info(tabulate(sorted(apic_vrf_not_deployed_list), headers = ["Tenant", "VRF", "Scope ID"], tablefmt="simple"))
    logger.info("#" * 80)

    # Print out the table with Tenant / VRF / Scope ID information for identified unenforced VRFs
    logger.info("Tenants/VRFs that have an 'implicit' + 'permit' + '{}' contract. Likely unenforced VRFs:".format(contract_search_type))
    logger.info("")
    if len(unenforced_vrfs) != 0:
        logger.info(tabulate(sorted(unenforced_vrfs), headers = ["Tenant", "VRF", "Scope ID"], tablefmt="simple"))
    else:
        logger.info("No VRFs found in unenforced mode")
    logger.info("#" * 80)

    # Print out the table with Tenant / VRF / Scope ID information to be reviewed manually
    logger.info("Tenants/VRFs that do NOT have a deployed 'default' + 'permit' + '{}' contract".format(contract_search_type))
    logger.info("")
    logger.info(tabulate(sorted(possibly_missing_contract), headers = ["Tenant", "VRF", "Scope ID"], tablefmt="simple"))
    logger.info("#" * 80)

    logger.info("Total of all contracts deployed across the entire Fabric: {}".format(len(query_response_all_contracts)))
    logger.info(("Total '{}' contracts deployed: {}".format(contract_search_type, len(query_response_specific_contracts))))
    logger.info(("Total '{}' contracts with 'permit' action and filterId as 'default' deployed: {}".format(contract_search_type, permit_counter)))
    logger.info("VRFs with '{}' default contracts deployed: {}".format(contract_search_type, len(tenants_with_deployed_default_contracts)))
    logger.info("#" * 25)
    logger.info("Number of Invalid ScopeIDs found deployed across the Fabric (eg: likely stale h/w entries): {}".format(len(stale_vrf_node_dict)))
    logger.info("Total VRFs configured on APIC: {}".format(len(tenant_info)))
    logger.info("VRFs configured on APIC but not deployed: {}".format(apic_vrf_not_deployed))
    #logger.info("VRFs deployed across the Fabric: {}".format(len(l3Ctx_nodes_dict)))
    logger.info("VRFs in unenforced mode: {}".format(len(unenforced_vrfs_scope)))
    logger.info("VRFs that should be deployed that also have VRFs with Default Contract correctly match both in Logical and Concrete models: {}".format(same_nodes_counter))
    logger.info("VRFs that should be deployed but have a mis-match on Node IDs: {}".format(different_nodes_counter))
    #logger.info("VRFs that should be deployed but have no nodes programmed: {}".format(no_nodes_counter))

    logger.info("Therefore possibly missing from {} VRFs - depending on configuration - as highlighted above. Please double check".format(len(possibly_missing_contract)))


def EPG_ENCAP_MISSING(session):
    '''
    Identify if the EPG (VLAN Encap) is missing from any nodes across the Fabric

    fvLocale dictates where the EPG should be deployed and on which node
    then compare the output of vlanCktEp and cross reference that each 

    An EPG without any bindings, does NOT have a fvLocale object created
    fvLocale only exists once an EPG is tied to a Dynamic/Static path binding (fvDyPathAtt or fvStPathAtt)
        This then dictates on which node/s should this EPG exist

    Obtain all fvLocale output, identifying the EPG DN and on which nodes it SHOULD exist
    then cross-reference that against the vlanCktEp output, which contains all EPGs deployed on all nodes
    ensure that they match. If any discrepencies, highlight the offending EPG and missing NODE/s

    NOTE: vlanCktPt only works for EPGs, not the other types reported in fvLocale. Example:
        EPG = fvAEPg (logical) -> fvEpP (resolved) -> vlanCktEp (concrete)
        L2out = l2extOut/l2extInstP (logical) -> fvBrEpP (resolved) -> ?? (concrete)
        L3out = l3extOut/l3extInstP (logical) -> fvRtdEpP (resolved) -> ?? (concrete)
        Inband = mgmtInB (logical) -> fvInBEpP (resolved) -> ?? (concrete)
        OOB = mgmtOoB (logical) -> fvOoBEpP (resolved) -> ?? (concrete)
    '''
    class_url_fvLocale = '/api/node/class/fvLocale.json?query-target=self'
    query_response_fvLocale = raw_apic_query(session, class_url_fvLocale)

    class_url_fvAEPg = '/api/node/class/fvAEPg.json?query-target=self'
    query_response_fvAEPg = raw_apic_query(session, class_url_fvAEPg)

    EPG_fvLocale_dict = {}
    L2out_fvLocale_dict = {}
    L3out_fvLocale_dict = {}
    Inband_fvLocale_dict = {}
    OOB_fvLocale_dict = {}
    counter_dict = {"EPG":0, "L2out":0, "L3out":0, "Inband":0, "OOB":0}

    for idx, fvLocale in enumerate(query_response_fvLocale):
        object_dn = str(fvLocale["fvLocale"]["attributes"]["dn"])
        node = str(re.search('node-([0-9]+)$', fvLocale["fvLocale"]["attributes"]["dn"]).group(1))
        # Strip the DN to only contain the real DN of the Logical Object
        logical_object_rn = re.search('\[[\S]+\]', object_dn).group(0)
        logical_object_rn = logical_object_rn.strip("[]")

        #print (object_dn)
        #print (logical_object_rn)
        #print (node + "\n")

        '''
        FvLocale DN could contain the following prefixes:

        EPG = 'uni/epp/fv-[uni/tn-mipetrin/ap-mipetrin/epg-EPG-V902]/node-101'
        L2out = 'uni/epp/br-[uni/tn-mipetrin/l2out-L2test/instP-L2test]/node-101'
        L3out = 'uni/epp/rtd-[uni/tn-mipetrin/out-mipetrin-L3test/instP-mipetrin-L3test]/node-204'
        INBAND = 'uni/epp/inb-[uni/tn-mgmt/mgmtp-default/inb-inband]/node-102'
        OOB = 'uni/epp/oob-[uni/tn-mgmt/mgmtp-default/oob-default]/node-3'

        Therefore store each in their own dictionary and then print them all out as required....

        VALIDATING
        EPG would have a vlanCktEp created to validate. The others do NOT
        Need to see what I have to compare it to at the concrete level

        moquery -c l3extInstP -x 'query-target-filter=and(wcard(l3extInstP.dn,"uni/tn-mipetrin/out-mipetrin-BFD-OSPF/instP-mipetrin-BFD-40"))'
        '''

        # Check what type of object the DN is currently pointing to, so can be stored in the correct dictionary
        if 'uni/epp/fv-[' in object_dn:
            # EPG
            counter_dict["EPG"] = counter_dict["EPG"] + 1

            if logical_object_rn not in EPG_fvLocale_dict:
                EPG_fvLocale_dict[logical_object_rn] = []

            EPG_fvLocale_dict[logical_object_rn].append(node)
        elif 'uni/epp/br-[' in object_dn:
            # L2out
            counter_dict["L2out"] = counter_dict["L2out"] + 1

            if logical_object_rn not in L2out_fvLocale_dict:
                L2out_fvLocale_dict[logical_object_rn] = []

            L2out_fvLocale_dict[logical_object_rn].append(node)
        elif 'uni/epp/rtd-[' in object_dn:
            # L3out
            counter_dict["L3out"] = counter_dict["L3out"] + 1

            if logical_object_rn not in L3out_fvLocale_dict:
                L3out_fvLocale_dict[logical_object_rn] = []

            L3out_fvLocale_dict[logical_object_rn].append(node)
        elif 'uni/epp/inb-[' in object_dn:
            # Inband
            counter_dict["Inband"] = counter_dict["Inband"] + 1

            if logical_object_rn not in Inband_fvLocale_dict:
                Inband_fvLocale_dict[logical_object_rn] = []

            Inband_fvLocale_dict[logical_object_rn].append(node)
        elif 'uni/epp/oob-[' in object_dn:
            # OOB
            counter_dict["OOB"] = counter_dict["OOB"] + 1

            if logical_object_rn not in OOB_fvLocale_dict:
                OOB_fvLocale_dict[logical_object_rn] = []

            OOB_fvLocale_dict[logical_object_rn].append(node)
        else:
            # Some other option that I haven't considered
            logger.warning("%% Error with the available options. Eg; Maybe L4-7 Devices?")
            logger.warning("DN type missed: {}".format(object_dn))

    if debug:
        print_header("EPG")
        if len(EPG_fvLocale_dict) == 0:
            logger.debug("\nNo EPG's found\n")
        else:
            print_epg_encap_missing(EPG_fvLocale_dict)

        print_header("L2out")
        if len(L2out_fvLocale_dict) == 0:
            logger.debug("\nNo L2out's found\n")
        else:
            print_epg_encap_missing(L2out_fvLocale_dict)

        print_header("L3out")
        if len(L3out_fvLocale_dict) == 0:
            logger.debug("\nNo L3out's found\n")
        else:
            print_epg_encap_missing(L3out_fvLocale_dict)

        print_header("Inband")
        if len(Inband_fvLocale_dict) == 0:
            logger.debug("\nNo Inband Management found\n")
        else:
            print_epg_encap_missing(Inband_fvLocale_dict)

        print_header("OOB")
        if len(OOB_fvLocale_dict) == 0:
            logger.debug("\nNo Out-of-Band Management found\n")
        else:
            print_epg_encap_missing(OOB_fvLocale_dict)

    logger.info("fvLocale count breakdown:")
    logger.info(counter_dict)
    logger.info("\n")

    # Use vlanCktEp to cross-reference against fvLocale for each EPG and where it should be deployed
    query_response_vlanCktEp = get_vlanCktEp(session)

    # Dictionary to maintain the EPG Encaps
    vlanCktEp_dict = {}

    # Loop over each Concrete object - vlanCktEp - which is the VLANs deployed on each switch
    for vlanCktEp in query_response_vlanCktEp:
        epg_dn = str(vlanCktEp["vlanCktEp"]["attributes"]["epgDn"])
        object_dn = str(vlanCktEp["vlanCktEp"]["attributes"]["dn"])
        node = re.search('node-([0-9]+)/', vlanCktEp["vlanCktEp"]["attributes"]["dn"]).group(1)
        node = str(node)

        #######
        '''
        NEED TO CONSIDER THE re.search to handle vpc nodes (node-101-102)..  if fix here, need to fix elsewhere
        '''
        #######

        if epg_dn not in vlanCktEp_dict:
            vlanCktEp_dict[epg_dn] = []
            logger.debug("EPG {} is being added".format(epg_dn))

        vlanCktEp_dict[epg_dn].append(node)

    if debug:
        for dn,node_ids in vlanCktEp_dict.iteritems():
            logger.debug("DN: {}".format(dn))
            logger.debug("Nodes: {}".format(node_ids))
            logger.debug("#" * 25)

    apic_epg_not_deployed = 0
    apic_epg_not_deployed_list = [] # Contain Tenant/Context/ScopeId

    logger.info("#" * 80)
    logger.info("EPGs Not Deployed on any node, only on APIC\n")

    for apic_config_epg in query_response_fvAEPg:
        apic_epg_name = str(apic_config_epg["fvAEPg"]["attributes"]["name"])
        apic_epg_dn = str(apic_config_epg["fvAEPg"]["attributes"]["dn"])
        #apic_epg_scope = str(apic_config_epg["fvAEPg"]["attributes"]["scope"])

        if apic_epg_dn not in EPG_fvLocale_dict.keys():
            # Means we have an EPG that is configured on APIC but not deployed on ANY node
            # Could be by design, not complete configuration, or an issue
            # Possibly flag for further investigation?
            logger.info("++ Name: {}".format(apic_epg_name))
            logger.info("---- EPG DN: {}\n".format(apic_epg_dn))
            apic_epg_not_deployed_list.append((apic_epg_dn, apic_epg_name))
            # Could print this out at a later stage to identify which EPGs exactly
            apic_epg_not_deployed += 1

    logger.info("#" * 80)

    # If EPG found in fvLocale for a node, but not in vlanCktEp for that node, it means 
    #       there is likely a fault (also being reported in APIC via nwissues fault). Double check these faults
    same_nodes_counter = 0
    different_nodes_counter = 0
    no_nodes_counter = 0
    for item_dn, item_nodes in EPG_fvLocale_dict.iteritems():
        # Need to test if it is actually in both dictionaries otherwise will throw error
        if item_dn in vlanCktEp_dict:
            # Check to see if nodes expected (fvLocale) vs deployed (vlanCktEp) are the same
            if sorted(item_nodes) == sorted(vlanCktEp_dict[item_dn]):
                logger.debug("Node IDs match in both dictionaries for EPG {}".format(item_dn))
                logger.debug("#" * 25)
                same_nodes_counter += 1
            else:
                #print ("Node ID mis-match for EPG: {}".format(item_dn))
                #print ("   Expected: {}".format(sorted(item_nodes)))
                #print ("     Actual: {}".format(sorted(vlanCktEp_dict[item_dn])))
                #print ("       Diff: {}".format(sorted(list_diff(sorted(item_nodes), sorted(vlanCktEp_dict[item_dn])))))
                #print ("#" * 25)
                logger.info("Node ID mis-match for EPG: {}".format(item_dn))
                logger.info("   Expected: {}".format(sorted(item_nodes)))
                logger.info("     Actual: {}".format(sorted(vlanCktEp_dict[item_dn])))
                logger.info("       Diff: {}".format(sorted(list_diff(sorted(item_nodes), sorted(vlanCktEp_dict[item_dn])))))
                logger.info("#" * 25)
                different_nodes_counter += 1
        else:
            # This fvLocale EPG DN does NOT exist in concrete vlanCktEp
            #print ("Not found programmed on any node for EPG: {}".format(item_dn))
            #print ("   Expected Nodes: {}".format(sorted(item_nodes)))
            #print ("#" * 25)
            logger.info("Not found programmed on any node for EPG: {}".format(item_dn))
            logger.info("   Expected Nodes: {}".format(sorted(item_nodes)))
            logger.info("#" * 25)
            no_nodes_counter += 1

    #print ("#" * 80)
    #print ("Total EPGs configured on APIC: {}".format(len(query_response_fvAEPg)))
    #print ("Total EPGs configured on APIC but not deployed anywhere: {}".format(apic_epg_not_deployed))
    #print ("EPGs that should be deployed that correctly match both in Logical and Concrete models: {}".format(same_nodes_counter))
    #print ("EPGs that should be deployed but have a mis-match on Node IDs: {}".format(different_nodes_counter))
    #print ("EPGs that should be deployed but have no nodes programmed: {}".format(no_nodes_counter))
    logger.info("#" * 80)
    logger.info("Total EPGs configured on APIC: {}".format(len(query_response_fvAEPg)))
    logger.info("Total EPGs configured on APIC but not deployed anywhere: {}".format(apic_epg_not_deployed))
    logger.info("EPGs that should be deployed that correctly match both in Logical and Concrete models: {}".format(same_nodes_counter))
    logger.info("EPGs that should be deployed but have a mis-match on Node IDs: {}".format(different_nodes_counter))
    logger.info("EPGs that should be deployed but have no nodes programmed: {}".format(no_nodes_counter))


def list_diff(li1, li2):
    '''
    Helper function to return the difference between two lists
    '''
    return (list(set(li1) - set(li2)))


def print_epg_encap_missing(concrete_dictionary):
    '''
    test print function during debugging
    '''

    #pprint (concrete_dictionary)
    for dn,node_ids in concrete_dictionary.iteritems():
        logger.debug("DN: {}".format(dn))
        logger.debug("Nodes: {}".format(node_ids))
        logger.debug("#" * 25)


def EPG_BD_MAPPING(session):
    '''
    Identify if the EPG to BD mapping is correct when comparing GUI output and node programming across the Fabric

    5) EPG to BD mapping on GUI is correct, in H/W is mis-programmed

    Check the output of the EPG to see the BD mapping (fvAEPg) and confirm the concrete EPG object on leaf and see if matching the BD_SEG_ID

    Logical: fvAEPg (DN) <- children -> fvRsBd <--> fvBD (Name/SegID)

    fvAEPg:
        dn	uni/tn-mipetrin/ap-mipetrin-vmm-ap/epg-vmm-102

    fvRsBd:
        tDn	uni/tn-mipetrin/BD-mipetrin-vmm-bd

    fvBD:
        dn: uni/tn-mipetrin/BD-mipetrin-vmm-bd
        name	mipetrin-vmm-bd
        seg	15728630

    Once build the above relationship, should only then have to validate against the vlanCktEp to confirm that the epgDn deployed (from above fvAEPg)
        matches the bd-[vxlan-(0-9)+] as defined in the fvBD output. If they do NOT match, we then have a problem

    Concrete: vlanCktEp <--> l2BD

    vlanCktEp:
        dn	topology/pod-2/node-202/sys/ctx-[vxlan-2392070]/bd-[vxlan-15728630]/vlan-[vlan-2678]
        epgDn	uni/tn-mipetrin/ap-mipetrin-vmm-ap/epg-vmm-202
        name	mipetrin:mipetrin-vmm-ap:vmm-202

    # Should not need to also cross reference the output of fvBD vs l2BD
    l2BD:
        dn	topology/pod-2/node-202/sys/ctx-[vxlan-2392070]/bd-[vxlan-15728630]
        fabEncap	vxlan-15728630
        name: mipetrin:mipetrin-vmm-bd
    '''
    # All EPGs configured across the ACI Fabric and the BD they are connected to
    class_url_all_epgs_with_bd = '/api/node/class/fvAEPg.json?rsp-subtree=children&rsp-subtree-class=fvRsBd'

    # Obtain all BDs as well, to then be able to pull the SegID
    class_url_all_bds = '/api/node/class/fvBD.json'

    # All concrete objects for EPGs deployed across the ACI Fabric
    #class_url_vlanCktEp = '/api/node/class/vlanCktEp.json?query-target=self'

    # Query the APIC to obtain the Managed Objects
    query_response_all_epgs_with_bd = raw_apic_query(session, class_url_all_epgs_with_bd)
    query_response_all_bds = raw_apic_query(session, class_url_all_bds)
    #query_response_vlanCktEp = raw_apic_query(session, class_url_vlanCktEp)
    query_response_vlanCktEp = get_vlanCktEp(session)

    '''
    # query_response_all_epgs_with_bd:
    {
        "fvAEPg": {
            "attributes": {
                "dn": "uni/tn-mipetrin/ap-CiscoLive_18/epg-CiscoLive_18-mike-test-db",
                "name": "CiscoLive_18-mike-test-db",
                "scope": "2916353",
            },
            "children": [
                {
                    "fvRsBd": {
                        "attributes": {
                            "tDn": "uni/tn-mipetrin/BD-CiscoLive_18_BD",
                            "tRn": "BD-CiscoLive_18_BD",
                            "tnFvBDName": "CiscoLive_18_BD",
                        }
                    }
                }
            ]
        }
    }

    # query_response_all_bds:
    {
        "fvBD": {
            "attributes": {
                "dn": "uni/tn-mipetrin/BD-mipetrin-vmm-bd",
                "name": "mipetrin-vmm-bd",
                "scope": "2392070",
                "seg": "15728630",
            }
        }
    }

    # query_response_vlanCktEp:
    {
        u 'vlanCktEp': {
            u 'attributes': {
                u 'dn': u 'topology/pod-1/node-102/sys/ctx-[vxlan-2293768]/bd-[vxlan-16580493]/vlan-[vlan-1302]',
                u 'encap': u 'vlan-1302',
                u 'epgDn': u 'uni/tn-mipetrin/ap-TEST/epg-EPG-Web',
                u 'name': u 'mipetrin:TEST:EPG-Web'
            }
        }
    }
    '''
    logical_bd_segId = {}

    for all_bds_apic in query_response_all_bds:
        bd_dn = str(all_bds_apic["fvBD"]["attributes"]["dn"])
        bd_name = str(all_bds_apic["fvBD"]["attributes"]["name"])
        bd_seg = str(all_bds_apic["fvBD"]["attributes"]["seg"])

        logger.debug("BD DN: {}".format(bd_dn))
        logger.debug("BD Name: {}".format(bd_name))
        logger.debug("BD SegID: {}".format(bd_seg))
        logger.debug("#" * 25)

        # Store in a dictionary with the SegID as the key, with the BD DN / Name as sub-keys
        if bd_dn not in logical_bd_segId:
            logical_bd_segId[bd_dn] = {}

        logical_seg_dict_tmp = {}
        logical_seg_dict_tmp['bd_name'] = bd_name
        logical_seg_dict_tmp['bd_seg'] = bd_seg
        logical_bd_segId[bd_dn].update(logical_seg_dict_tmp)

    logging.debug("\n" + pformat(logical_bd_segId, indent=4)) # if debug: pprint (logical_bd_segId)

    logical_epg_bd_mapping_dict = {}
    bd_error_counter = 0

    for epg_bd_mapping_apic in query_response_all_epgs_with_bd:
        epg_dn = str(epg_bd_mapping_apic["fvAEPg"]["attributes"]["dn"])
        epg_name = str(epg_bd_mapping_apic["fvAEPg"]["attributes"]["name"])
        target_bd_dn = str(epg_bd_mapping_apic["fvAEPg"]["children"][0]["fvRsBd"]["attributes"]["tDn"])
        target_bd_name = str(epg_bd_mapping_apic["fvAEPg"]["children"][0]["fvRsBd"]["attributes"]["tnFvBDName"])

        logger.debug("EPG DN: {}".format(epg_dn))
        logger.debug("EPG Name: {}".format(epg_name))
        logger.debug("Target BD DN: {}".format(target_bd_dn))
        logger.debug("Target BD Name: {}".format(target_bd_name))
        logger.debug("#" * 25)

        # Loop through each EPG and start to store the DN in a Dictionary as the key, and target DN as a nested dictionary
        if epg_dn not in logical_epg_bd_mapping_dict:
            logical_epg_bd_mapping_dict[epg_dn] = {}

        logical_encapDict_Tmp = {}
        logical_encapDict_Tmp['target_bd'] = target_bd_dn

        if target_bd_dn in logical_bd_segId:
            logical_encapDict_Tmp['bd_seg'] = logical_bd_segId[target_bd_dn]["bd_seg"]
        else:
            logger.info("Found a BD that isn't in the SegID dictionary due to no target BD DN found on APIC. Manually check that the BD exists")
            logger.info("EPG Name: '{}' is configured for BD: '{}' but the following target BD DN is missing: '{}'\n".format(epg_dn,target_bd_name,target_bd_dn,))
            bd_error_counter += 1

        logical_epg_bd_mapping_dict[epg_dn].update(logical_encapDict_Tmp)

    logging.debug("\n" + pformat(logical_epg_bd_mapping_dict, indent=4)) #pprint(logical_epg_bd_mapping_dict)
    '''
    {
        epgDN:{
            "target_bd":name,
            "bd_seg":segId
        }
    }
    '''

    vlanCktEp_BD_mapping_dict = {}
    mismatch_counter = 0
    error_counter = 0

    for vlanCktEp in query_response_vlanCktEp:
        object_name = str(vlanCktEp["vlanCktEp"]["attributes"]["name"])
        epg_dn = str(vlanCktEp["vlanCktEp"]["attributes"]["epgDn"])
        access_encap = str(vlanCktEp["vlanCktEp"]["attributes"]["encap"])
        node = re.search('node-([0-9]+)/', vlanCktEp["vlanCktEp"]["attributes"]["dn"]).group(1)
        bd_vxlan = re.search('bd-\[vxlan-([0-9]+)\]/', vlanCktEp["vlanCktEp"]["attributes"]["dn"]).group(1)
        object_dn = str(vlanCktEp["vlanCktEp"]["attributes"]["dn"])

        if epg_dn in logical_epg_bd_mapping_dict:
            if logical_epg_bd_mapping_dict[epg_dn]["bd_seg"] != bd_vxlan:
                logger.info("Found a mis-matched BD to EPG mapping")
                #logger.debug("EPG: {}".format(epg_dn))
                #logger.debug("Node: {}".format(node))
                #logger.debug("Logical EPG -> BD SegID: {}".format(logical_epg_bd_mapping_dict[epg_dn]["bd_seg"]))
                #logger.debug("Hardware Programming EPG -> BD SegID: {}".format(bd_vxlan))
                logical_bd_vxlan = logical_epg_bd_mapping_dict[epg_dn]["bd_seg"]
                logger.info("Node {}, EPG: {}, Incorrect VXLAN VNID -> Expected 'Logical' ({}) vs Programmed in 'Hardware' ({})".format(node, epg_dn, logical_bd_vxlan, bd_vxlan))

                # instead add this to another list and then summary print at the end or state there are no issues
                logger.info("#" * 25 + "\n")
                mismatch_counter += 1
        else:
            # NOTE need to consider L4-L7 concrete devices?
            # NOTE need to consider L2out/L3out
            # Believe that is why I get entries at this level, as they're not represented by vlanCktEp but other concrete objects
            # TO DO - then double check against the other Concrete object types
            logger.info("#" * 25)
            logger.info("Found an EPG that isn't in the Logical EPG to BD Mapping Dictionary. Manually check if any issue. Likely L2/L3 out")
            logger.info("Node {}, EPG '{}'".format(node, epg_dn))
            logger.info("Access Encap: '{}'\n".format(access_encap))
            #logger.info ("Object DN: '{}'".format(object_dn))
            error_counter += 1

    logger.info("#" * 80)
    logger.info("BD Errors, likely due to EPG pointing to a BD with Target missing: {}".format(bd_error_counter))
    logger.info("Errors detected outside of BD - EPG Mapping: {}".format(error_counter))
    logger.info("Mis-match mapping errors detected between BD - EPG: {}".format(mismatch_counter))


def ALL(session):
    '''
    Perform every check available
    '''
    print_header("EPG_VXLAN_ENCAP")
    EPG_VXLAN_ENCAP(session)

    print_header("BD_VXLAN_ENCAP")
    BD_VXLAN_ENCAP(session)

    print_header("VZANY_MISSING")
    VZANY_MISSING(session)

    print_header("EPG_ENCAP_MISSING")
    EPG_ENCAP_MISSING(session)

    print_header("EPG_BD_MAPPING")
    EPG_BD_MAPPING(session)


def main():
    '''
    Main Function
    '''
    description = ('Application to check that various elements are correctly programmed')
    creds = Credentials('apic', description)
    creds.add_argument('-v', '--version', action='version', version='%(prog)s == {}'.format(__version__))
    creds.add_argument('--log', action='store_true', help='Write the output to a log file: {}.log. Automatically adds timestamp to filename'.format(__file__.split(".py")[0]))
    creds.add_argument('--list', action='store_true', help='Print out the list of checks that can be performed')
    creds.add_argument("--debug", dest="debug", choices=["debug", "info", "warn", "critical"], default="info", help='Enable debugging output to screen')
    #creds.add_argument('--filter', choices=["node", "tenant", "none"], default="none", help='Specify what to filter on. Default = none')
    creds.add_argument('--check', choices=["EPG_VXLAN_ENCAP", "BD_VXLAN_ENCAP", "VZANY_MISSING", "EPG_ENCAP_MISSING", "EPG_BD_MAPPING", "ALL"], default="all", help='Specify which checks to perform. Default = all')
    args = creds.get()

    # Set up custom logger
    setup_logger(logger, args.debug, args.log)

    # Can't prevent the system for asking for password first, as that is part of the ACIToolkit code happening with creds.get()
    # Determine if the use wants to simply print out the list of checks currently available
    if args.list:
        print_checks_available()
        exit(0)

    # Login to APIC
    session = Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        logger.critical('%% Could not login to APIC')
        my_error = resp.json()
        logger.critical("%% Error: {}".format(my_error["imdata"][0]["error"]["attributes"]["text"]))
        sys.exit(0)

    # Start time count at this point, otherwise takes into consideration the amount of time taken to input the password
    start_time = time.time()

    # Perform the relevant tests based on the selection made
    #global debug
    #debug = args.debug
    #if args.debug:
    #    print ("Debugging is enabled...")
    logger.debug("Debugging is enabled...")

    if args.check == "EPG_VXLAN_ENCAP":
        EPG_VXLAN_ENCAP(session)
    elif args.check == "BD_VXLAN_ENCAP":
        BD_VXLAN_ENCAP(session)
    elif args.check == "VZANY_MISSING":
        VZANY_MISSING(session)
    elif args.check == "EPG_ENCAP_MISSING":
        EPG_ENCAP_MISSING(session)
    elif args.check == "EPG_BD_MAPPING":
        EPG_BD_MAPPING(session)
    elif args.check == "ALL":
        ALL(session)
    else:
        #print ("Something went wrong with the choices you've selected")
        logger.warning("Something went wrong with the choices you've selected")

    logger.info("\n")
    if args.log:
        #print ("#" * 80)
        logger.info("#" * 80)
        logger.info("Log file written: {}".format(logging_filename))

    #print ("#" * 80)
    #finish_time = time.time()
    #print ("Started analysis @ {}".format(time.asctime(time.localtime(start_time))))
    #print ("Ended analysis @ {}".format(time.asctime(time.localtime(finish_time))))
    #print("--- Total Execution Time: %s seconds ---" % (finish_time - start_time))
    #print ("#" * 80)

    logger.info("#" * 80)
    finish_time = time.time()
    logger.info("Started analysis @ {}".format(time.asctime(time.localtime(start_time))))
    logger.info("Ended analysis @ {}".format(time.asctime(time.localtime(finish_time))))
    logger.info("--- Total Execution Time: %s seconds ---" % (finish_time - start_time))
    logger.info("#" * 80)

if __name__ == '__main__':
    main()