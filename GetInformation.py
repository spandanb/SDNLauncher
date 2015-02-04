#!/usr/bin/env python

# Copyright (c) 2014 University of Toronto.
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

'''
SDNLauncher.py
===============
This script parses both topology.py and config.py and sets up the user defined
topology. After the VMs are launched, it establishes the connections via Vxlan

@author: Khashayar Hossein Zadeh <k.hosseinzadeh@mail.utoronto.ca>

'''

# vim: tabstop=4 shiftwidth=4 softtabstop=4 expandtab */

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

from config import user, password, auth_url 
from config import instance_name, key_name, private_key_file, pub_key, key_name
from config import image_name, flavor_name, sec_group_name, vm_user_name, wait_before_ssh
from config import tenant_name, region_name 

from keystoneclient.v2_0 import client as ksclient
import re
from prettytable import PrettyTable
from topology import topology, nodes


def print_msg(msg):
    #pass
    print msg

"""
Here we parse the 'topology' dictionary found inside topology.py and extract 
a list 'nodeList' which stores the names of every Node
"""
# parse the user topology
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


try:
    with open(private_key_file) as f:
        private_key = f.read()
except:
    print "cant open key file: %s" %private_key_file
    sys.exit(0)


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


def check_host(server, host):
        server.get()
        if hasattr(server, "OS-EXT-SRV-ATTR:host"):
                return getattr(server, "OS-EXT-SRV-ATTR:host") == host
        return False

def checkServer(server):
        server.get()
        if hasattr(server, "fault"):
            print_msg("error fault is " + str(getattr(server, "fault")) + "\n")

def _calc_vni(node):
    vn1 = 0
    if node.lower().startswith('sw'):
       vn1=node.lower()
       vn1=int(vn1[2:]) + 500
    elif node.lower().startswith('h'):
       vn1=node.lower()
       vn1=int(vn1[1:])
    return vn1


num_links={}

def _get_vni(node1, node2):
    vn1=_calc_vni(node1)
    vn2=_calc_vni(node2)
    d1=num_links.setdefault(node1, {})
    d2=d1.setdefault(node2, 0)
    num_links[node1][node2] += 1
    if vn1 < vn2:
        vn = vn1 * 16384 + vn2 * 16 + d2
    else:
        vn = vn2 * 16384 + vn1 * 16 + d2
    print "%s --> %s : %s" %(node1, node2, vn)
    return vn

ports={}
u_dict={}

"""
This function takes in a switch name, in the format 'sw#', ex: 'sw1' and runs several
ovs-vsctl commands. It starts off by adding our bridge, then sets up a controller address which the
switch connects to (if it was specified as none inside the topology.py file, we do not implement this).

The two for loops inside this function establish a vxlan configuration for every node this switch connects to.
The first for loop takes care of the connections found inside the topology[sw#] = '.... establishes everything here....'
and the second for loop establishes the connections to that switch found in another switch's dictionary values.

Example:
topology['sw1'] = [('h1', '192.168.200.10'),'sw3']
topology['sw2'] = ['sw1']
topology['sw3'] = [('h2', '192.168.200.11')]

The first for loop establishes the vxlands for h1 and sw3 and the second for loop
establishes the connection to sw2
"""
def setupSwitch(switch):
        print "working on switch %s\n" %switch
        fixed_ip= fxdict[switch]
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(fixed_ip, username=u_dict.get(switch, vm_user_name), key_filename=private_key_file)
        time.sleep(2)
        # running the ovs commands
        if switch not in nodes:
            print "Switch %s was not defined in 'nodes', setting up using default ovs commands" % switch
        bridge_name = 'br1'
        if 'bridge_name' in nodes[switch]:
            bridge_name = nodes[switch]['bridge_name']
        stdin, stdout, stderr = ssh.exec_command("sudo ovs-vsctl get bridge %s datapath_id" % bridge_name)
        stdin.close()
        dpid=(''.join(stdout.readlines())).strip("\n");
        print "datapath_id of %s is %s\n" %(bridge_name, dpid)
        time.sleep(1)
        if 'int_ip' in nodes[switch]:
            int_ip_name = nodes[switch]['int_ip'][0]
            int_ip = nodes[switch]['int_ip'][1]
            #ssh.exec_command("sudo ovs-vsctl add-port %s %s -- set interface %s type=internal " % (bridge_name,int_ip_name, int_ip_name))
            #time.sleep(1)     
            stdin, stdout, stderr = ssh.exec_command("sudo ovs-vsctl get interface %s mac_in_use" % (int_ip_name));
            stdin.close()
            stdin2, stdout2, stderr2 = ssh.exec_command("sudo ovs-vsctl get interface %s ofport" % (int_ip_name));
            stdin.close()
            mac=(''.join(stdout.readlines())).strip("\n")
            of_port=(''.join(stdout2.readlines())).strip("\n")
            print "mac of %s is %s, of port is %s\n" %(int_ip, mac, of_port)
            ports.setdefault(int_ip, {})
            ports[int_ip]['dpid']=dpid
            ports[int_ip]['mac']=mac
            ports[int_ip]['of_port']=of_port
            time.sleep(1) 
        # this will hold the internal ip for use in the vxlan set up
        connectip = ''
        # this is used for the vxlan count and VLNI number (this must be the same on both sides)
        vlni = 0
        # used to implement a different VLNI number. For the cases of multiple connections to the same node
        vnlilist = []
        # this 'host' is every node consisting of triplette or switch name for that switch
        for host in topology[switch]:
            # handle hosts 
            if isinstance(host, tuple):
                #vlni = int(host[0][1]) + int(switch[2]) + (2*numSwitches) + 10
                #vlni += vnlilist.count(vlni)
                #vnlilist.append(vlni)
                vlni = _get_vni(host[0], switch)
                connectip = fxdict[host[0]]
                ip_of_port = host[1] 
                stdin, stdout, stderr = ssh.exec_command("sudo ovs-vsctl get interface vxlan%s ofport" % (vlni))
                stdin.close()
                of_port=(''.join(stdout.readlines())).strip("\n")
                print "of port to %s is %s\n" %(ip_of_port, of_port)
                ports.setdefault(ip_of_port, {})
                ports[ip_of_port]['dpid']=dpid
                ports[ip_of_port]['of_port']=of_port
            # handle switches
            else: 
                #vlni = int(host[2]) + int(switch[2]) + 10
                #vlni += vnlilist.count(vlni)
                #vnlilist.append(vlni)
                vlni = _get_vni(host, switch)
                connectip = fxdict[host]
            time.sleep(1)
        # establishes all the other connections to this switch 
        for keys in topology.keys():
            for host in topology[keys]:
                if (host == switch):
                    connectip = fxdict[keys]
                    #vlni = int(keys[2]) + int(switch[2]) + 10 
                    #vlni += vnlilist.count(vlni)
                    #vnlilist.append(vlni)
                    vlni = _get_vni(keys, switch)
                    #ssh.exec_command("sudo ovs-vsctl add-port %s vxlan%s -- set interface vxlan%s type=vxlan options:remote_ip=%s options:key=%s" % (bridge_name, vlni, vlni,connectip, vlni))
                    stdin, stdout, stderr = ssh.exec_command("sudo ovs-vsctl get interface vxlan%s ofport" % (vlni))
                    stdin.close()
                    print "of port to %s is %s\n" %(connectip, (''.join(stdout.readlines())))
                    time.sleep(1)
        ssh.close()

"""
This function takes in a host name, in the format 'h#', ex: 'h1' and runs several
ovs-vsctl commands. It starts off by adding a bridge and internal port for every connection
to/from this host. The internal IP can be set to none, in this case we do not implement it

The for loop inside this function performs the exact same as the 2nd for loop inside setupSwitches
"""
def setupHosts(host):
        print "working on host %s\n" %host
        fixed_ip= fxdict[host]
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(fixed_ip, username=u_dict.get(host, vm_user_name), key_filename=private_key_file)
        time.sleep(3)
        # running the ovs commands
        count = 0
        connectip = ''
        vlni = 0
        vnlilist = []
        for keys in topology.keys():
            # this 'hosts' is every node consisting of triplette or switch name for that switch
            for hosts in topology[keys]:
                # if true, this is a triplette belonging to this desired host
                if (hosts[0] == host):
                    # third element is the bridge name
                    try:
                        if hosts[2]:
                            bridge_name = hosts[2]
                    except:
                        bridge_name = 'br%s' % count
                    stdin, stdout, stderr = ssh.exec_command("sudo ovs-vsctl get interface p%s mac_in_use" % (count));
                    mac=(''.join(stdout.readlines())).strip("\n")
                    print "mac of %s is %s" %(hosts[1], mac)
                    ports.setdefault(hosts[1], {})
                    ports[hosts[1]]['mac']=mac
                    connectip = fxdict[keys]
                    #vlni = int(keys[2]) + int(host[1]) + (2*numSwitches) + 10
                    #vlni += vnlilist.count(vlni)
                    #vnlilist.append(vlni)
                    vlni = _get_vni(keys, host)
                    count += 1
        ssh.close()


print "\n\n"
print "----------- NETWORK TOPOLOGY -----------\n"

"""
Give a nice print out of the topology when this script runs
"""
# sort through the switch names since they become scrambled inside a Dict
tempsortlist = []
tempsortlist = topology.keys()
tempsortlist.sort()
for item in tempsortlist:
    print item + ' connects to these nodes (bidirectional):  ', topology[item]
print "\n"


# holds the internal ips for each VM... key = node name, value = internal ip
fxdict= {}
i_name_dict={}
vmdict={}
# backup of the default parameters as specified inside the config.py file
fixedRegion_name = region_name
fixedimage_name = image_name
fixedflavor_name = flavor_name
fixedInstancename = instance_name

if True:       
        s1 = None
        quantum = None
        try:
            # this list holds the servers (vms)
            servers_list=[]
            # this list holds each node's pretty table object
            table_list = []
            finished_servers = []
            # launch all of the VMs without checking the active state
            for i in range(numNodes): 
                """
                Parse the 'nodes' dictionary as defined in the topology.py file
                and set the variables before that specific VM launches
                """
                nodeName = nodeList[i]
                u_name = vm_user_name
                try:
                    if nodeName in nodes: 
                        u_name = nodes[nodeName].get('vm_user_name', vm_user_name)
                        if 'region' in nodes[nodeName]:
                            region_name = nodes[nodeName]['region']
                        else:
                            region_name = fixedRegion_name

                        if 'flavor' in nodes[nodeName]:
                            flavor_name = nodes[nodeName]['flavor']
                        else:
                            flavor_name = fixedflavor_name

                        if 'image' in nodes[nodeName]:
                            image_name = nodes[nodeName]['image']
                        else:
                            image_name = fixedimage_name
                        if 'name' in nodes[nodeName]:
                            instance_name = nodes[nodeName]['name']
                        else:
                            instance_name = fixedInstancename + "%s" % (nodeName)
                    else:
                        region_name = fixedRegion_name
                        flavor_name = fixedflavor_name
                        image_name = fixedimage_name
                        instance_name = fixedInstancename + "%s" % (nodeName)
                except:
                    print "\n\n --------- ERROR IN THE NODES DICTIONARY on key %s-------------" %nodeName
                    print " using defualt parameters to launch"
                    region_name = fixedRegion_name
                    flavor_name = fixedflavor_name
                    image_name = fixedimage_name
                    instance_name = fixedInstancename + "%s" % (nodeName)
                                    

                c=nclient.Client(user, password, tenant_name, auth_url, region_name=region_name, no_cache=True)
                #instance_name = fixedInstancename + "%s" % (nodeName)
                print_msg("\nTesting VM %d/%d (%s / %s) on region: %s" % (i+1, numNodes, nodeName, instance_name, region_name))

                i_name_dict[instance_name]=nodeName
                #create quantum client for floating ip address creation/association and VM network
                quantum=qclient.Client(username=user, password=password, tenant_name=tenant_name, auth_url=auth_url, region_name=region_name)
                #look for network id of the external network
                _network_id = quantumv20.find_resourceid_by_name_or_id(quantum, 'network', tenant_name+'-net')
                v_nics=[]
                v_nic={}

                x = PrettyTable(["Property", "Value"])
                x.add_row(["Node", nodeName])
                x.add_row(["VM name", instance_name])
                x.add_row(["VM number", i+1])
                x.add_row(["Network ID",_network_id])
                v_nic['net-id']=_network_id
                v_nic['v4-fixed-ip']=None
                v_nics.append(v_nic)
                #print s1

                servers=c.servers.list()
                s1=None
                for server in servers:
                    if server.name == instance_name:
                        s1 = server
                        print "found\n"
                        break
                if s1 is None or s1.name != instance_name:
                    print "cant find this server: %s\n" %instance_name
                    sys.exit(0)
                x.add_row(["VM ID",s1.id])
                # note, here we do not have the internal ips. So we specify the server id with that node's name
                vmdict["%s" % (nodeName)] = s1.id
                u_dict[nodeName] = u_name
                servers_list.append(s1)
                table_list.append(x)
            
            # Wait until every VM has booted up. Checks the active/error state of the VMs
            fixed_ip = None
            srv_cnt = 0
            for i in range (1, 50):
                srv_cnt = 0
                for s1 in servers_list:
                    s1.get()
                    if s1.status == "ERROR":
                        srv_cnt += 1
                        if s1.id in finished_servers:
                           continue;
                        finished_servers.append(s1.id)
                        print_msg("server is in error")
                    elif s1.status == "ACTIVE":
                        srv_cnt += 1
                        if s1.id in finished_servers:
                           continue;
                        finished_servers.append(s1.id)
                        (s_net, s_ip)=s1.networks.popitem()
                        if fixed_ip is None:
                            fixed_ip = s_ip[0]
                if srv_cnt >= len(servers_list):
                    print_msg("All servers are done")
                    break    
                print_msg("server count is %s/%s " % (srv_cnt, numNodes))
                time.sleep(1)

            # This forloop updates our 'fxdict' dict and matches the internal ips with that node name
            tempcount = 0
            for s1 in servers_list:
                s1.get()
                if s1.status == "ACTIVE":
                   (s_net, s_ip)=s1.networks.popitem()
                   # add in the internal ip for that node 
                   for key in vmdict:
                        if (vmdict[key] == s1.id):
                            fxdict[key] = s_ip[0]            
                   checkServer(s1)                       #-----------------------------
                   table_list[tempcount].add_row(["Host",str(getattr(s1, "OS-EXT-SRV-ATTR:host"))])
                   table_list[tempcount].add_row(["Instance Name",str(getattr(s1, "OS-EXT-SRV-ATTR:instance_name"))])
                   table_list[tempcount].add_row(["Interal IP addr", s_ip[0]])
                   tempcount += 1

            # get a list of port id in quantum
            q_ports=quantum.list_ports()

            #look for the port is of the server port
            for port in q_ports['ports']:
                    ips=port['fixed_ips']
                    for ip in ips:
                        if ip['ip_address'] == fixed_ip:
                                pid=port['id']
                                break

            # loop over and print out the tables. They are in the pretty table format
            tempcount = 0
            for s1 in servers_list:
                print table_list[tempcount]
                print "\n"
                tempcount += 1

            #look for network id of the external network
            _network_id = quantumv20.find_resourceid_by_name_or_id(quantum, 'network', 'ext_net')

            print fxdict
            wait_before_ssh=3
            for s1 in []: #servers_list:
                print s1
                #s1 = servers_list[-1]
                #fixed_ip = fxdict.values()[-1]
                fixed_ip = fxdict[i_name_dict[s1.name]]
                print_msg("waiting %d seconds before ssh test" %wait_before_ssh)
                time.sleep(wait_before_ssh)

                try:
                    for i in range (1, 5):
                        s1.get()
                        server_console_output = s1.get_console_output()
                        if s1.status == "ACTIVE" and ("Generation complete." not in server_console_output):
                            if fixed_ip not in s1.get_console_output():
                                print_msg("failed to get dhcp address %s \n" % fixed_ip)
                            if "waiting 120 seconds for a network device" in server_console_output:
                                print_msg("strange!: waiting 120 seconds for a network device")
                            #print_msg("Please be patient, waiting another %d seconds \n" % wait_before_ssh)
                            break
                        elif s1.status == "ACTIVE":
                            print_msg("Server console-log is fine: %s, %s, %s \n" %(s1.id, s1.name, fixed_ip))
                            if fixed_ip not in s1.get_console_output():
                            #shouldnt get here if key genration comepleted fine
                                print_msg("failed to get dhcp address %s \n" % fixed_ip)
                            break
                        time.sleep(wait_before_ssh)
                except:
                    msg = msg + "\n exception in console-log check\n"
                    pass

                #ping fixed ip and print output
                if fixed_ip is not None:
                    str2="ping to fixedip %s failed " % fixed_ip 
                    try:
                        str1=subprocess.check_output(['ping', '-c 3', fixed_ip])
                    except:
                        pass
                    try:
                        str1=subprocess.check_output(['ping', '-c 3', fixed_ip])
                        str2=str1
                    except:
                        pass
                    print_msg(str2)

                    #ssh to the server and execute a couple of commands for sanity test
                    print_msg("starting ssh test")
                    out1 = ""
                    out2 = ""
                    try:
                        ssh = paramiko.SSHClient()
                        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                        ssh.connect(fixed_ip, username=u_dict.get(i_name_dict[s1.name], vm_user_name), key_filename=private_key_file)
                        time.sleep(1)
    
                        stdin, stdout, stderr = ssh.exec_command("uptime")
                        stdin.close()
                        out1=stdout.readlines()
                        print_msg("uptime output is: %s" % (''.join(out1)))
                        time.sleep(1)
    
                        stdin, stdout, stderr = ssh.exec_command("ping -c2 www.google.ca")
                        stdin.close()
                        out2=stdout.readlines()
                        print_msg("ping output is: %s" % (''.join(out2)))
                        ssh.close() 
                        # running the ovs commands
                    except:
                        print_msg("Ssh failed. If the edge is overloaded, allocate more time before the SSH check")
    
            # set up the controllers
            # the value "switch" being passed in is in the form of 'sw#'
            for switch in topology.keys():
                setupSwitch(switch) 
                        
            # set up the hosts
            # the value "host" being passed in is in the form of 'h#'
            for host in hostList:
                setupHosts(host)    

            #print ports
            print "\n"
            for port_ip, val in ports.iteritems():
                print "ip=\"%s\";mac=%s;dpid=%s;port=%s\n" % (port_ip, val['mac'], val['dpid'],val['of_port'])
            print "\nAll Finished, you can now access your VMs \n\n"
                        
        except:
            print "Failed to launch VMs. Check your keystone credentials"
            raise
