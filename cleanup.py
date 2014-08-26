#!/usr/bin/env python

# Copyright (c) 2014 University of Toronto
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# vim: tabstop=4 shiftwidth=4 softtabstop=4 expandtab

import novaclient.v1_1.client as nclient
import novaclient.v1_1.shell as nshell
import time
import paramiko
import sys
import subprocess
from quantumclient.v2_0 import client as qclient
import smtplib
from quantumclient.quantum import v2_0 as quantumv20
from novaclient import exceptions
from keystoneclient.v2_0 import client as ksclient
import re


from topology import topology, nodes
from config import region_name
from config import user, password, auth_url, instance_name, tenant_name

if len(sys.argv) > 1:
    instance_name = sys.argv[1] 

valuelist = []
for values in topology.values():
    for tuples in values:
        # we only want the hosts
        if isinstance(tuples, tuple):
            if ((tuples[0][0] == 'h' or tuples[0][0] == 'H') and tuples[0] not in valuelist):
                valuelist.append(tuples[0])

numHosts = len(valuelist)
numSwitches = len(topology.keys())
numNodes = numHosts + numSwitches

# this list contains the switch names and host names
nodeList = []
# start off by appending the switche names
for key in topology.keys():
    if (key not in nodeList):
        nodeList.append(key)

# this list only holds the host names (used to append into the nodeList)
hostList = []
for values in topology.values():
    for tuples in values:
        if isinstance(tuples, tuple):
            if ((tuples[0][0] == 'h' or tuples[0][0] == 'H') and tuples[0] not in hostList):
                hostList.append(tuples[0])

hostList.sort()
for elem in hostList:
    nodeList.append(elem)


regionlist = []
regionlist.append(region_name)
for values in nodes.values():
    if 'region' in values:
        if values['region'] not in regionlist:
            regionlist.append(values['region'])

names=[]
for node in nodeList:
    names.append(nodes[node].get('name', "%s%s" %(instance_name, node)))

for region_name in regionlist:
        c2=nclient.Client(user, password, tenant_name, auth_url, region_name=region_name, no_cache=True)
        servers=c2.servers.list()
        for server in servers:
            if server.name in names:
                print "Deleting VM %s " % server.name
                server.delete() 
