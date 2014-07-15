#!/usr/bin/env python

import novaclient.v1_1.client as nclient
import novaclient.v1_1.shell as nshell
import time
import sys
from quantumclient.v2_0 import client as qclient
from quantumclient.quantum import v2_0 as quantumv20
from novaclient import exceptions

import whaleclient
import whaleclient.exc
from keystoneclient.v2_0 import client as ksclient
import re
from prettytable import PrettyTable

user=''
password=''
auth_url='http://iam.savitestbed.ca:5000/v2.0/'
regions_list=[]
regions_list.append('EDGE-TR-1')
region_name = 'EDGE-TR-1'
test_tenant = 'demo1'
key_name="khash"
sec_group_name="default"

def print_msg(msg):
    #pass
    print msg


# three functions needed for whale client connection
def _strip_version(endpoint):
        """Strip a version from the last component of an endpoint if present"""

        # Get rid of trailing '/' if present
        if endpoint.endswith('/'):
            endpoint = endpoint[:-1]
        url_bits = endpoint.split('/')
        # regex to match 'v1' or 'v2.0' etc
        if re.match('v\d+\.?\d*', url_bits[-1]):
            endpoint = '/'.join(url_bits[:-1])
        return endpoint


def _get_ksclient(**kwargs):
        """Get an endpoint and auth token from Keystone.

        :param username: name of user
        :param password: user's password
        :param tenant_id: unique identifier of tenant
        :param tenant_name: name of tenant
        :param auth_url: endpoint to authenticate against
        """
        return ksclient.Client(username=kwargs.get('username'),
                               password=kwargs.get('password'),
                               tenant_id=kwargs.get('tenant_id'),
                               tenant_name=kwargs.get('tenant_name'),
                               auth_url=kwargs.get('auth_url'),
                               insecure=kwargs.get('insecure'))

def _get_endpoint(client, **kwargs):
        """Get an endpoint using the provided keystone client."""

        service_type = kwargs.get('service_type') or 'configuration'
        endpoint_type = kwargs.get('endpoint_type') or 'publicURL'
        region = kwargs.get('region')
        if region is not None:
                endpoint = client.service_catalog.url_for(
                             attr='region',
                             filter_value=region, 
                             service_type=service_type,
                             endpoint_type=endpoint_type)
        else:
                endpoint = client.service_catalog.url_for(
                             service_type=service_type,
                             endpoint_type=endpoint_type)

        return _strip_version(endpoint)

for region_name in regions_list:
        kwargs = {
                'username': user,
                'password': password,
                'region': region_name,
                'tenant_name': test_tenant,
                'auth_url': auth_url,
            }
        _ksclient = _get_ksclient(**kwargs)
        token = _ksclient.auth_token
        endpoint = _get_endpoint(_ksclient, **kwargs)
        #token = 'efe79676d79b40d881998884b1a86314' # for core
        #token = 'c4708de70626486a9f856cc4f3f50057' # for edge 1
        #endpoint = 'http://tr-core-1.savitestbed.ca:8976/v1.0'
        kwargs = {'token': token}
        client = whaleclient.Client('1', endpoint, **kwargs)
        serverlist = client.conf.get_nodes_by_type('SERVER')
        table = PrettyTable(["Active agents inside region: %s" %region_name])
        time.sleep(1)
        tempList = []
        for i in range(len(serverlist)):
                if serverlist[i]['servername'].isdigit():
                        continue;
                tempList.append(serverlist[i]['servername'])
                #print_msg("%s" % serverlist[i]['servername'])
                table.add_row(["%s" % serverlist[i]['servername']])                

        if region_name == "EDGE-VC-1":
                newTempList = []
                for servername in tempList:
                        newTempList.append(servername+'.savitestbed.ca')
                        table.add_row([servername+'.savitestbed.ca'])
                tempList = newTempList
        print table
