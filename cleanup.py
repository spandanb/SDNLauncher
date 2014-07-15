#!/usr/bin/env python

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
import whaleclient
import whaleclient.exc
from keystoneclient.v2_0 import client as ksclient
import re


from topology import topology, nodes
from config import region_name
from config import user, password, auth_url, instance_name, tenant_name

if sys.argv[1]:
    instance_name = sys.argv[1] 

regionlist = []
regionlist.append(region_name)
for values in nodes.values():
    if 'region' in values:
        if values['region'] not in regionlist:
            regionlist.append(values['region'])

for region_name in regionlist:
        c2=nclient.Client(user, password, tenant_name, auth_url, region_name=region_name, no_cache=True)
        servers=c2.servers.list()
        for server in servers:
            if instance_name in server.name:
                server.delete() 
                print "Deleting VM %s " % server.name
