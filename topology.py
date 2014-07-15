#!/usr/bin/env python

# vim: tabstop=4 shiftwidth=4 softtabstop=4 expandtab

#  ----------------------- topology dict ------------------
"""
The Keys of the topology dictionary can only be switches

The values represent the connection to/from that switch. To create a link to another switch,
just write the switch#. To represent a connection to a host, write down a tuple containing the
host# and internal port address. An optional field for the host is the bridge name at tuple index 2.
The other two fields are mandatory

topology['switch number'] = [ ( 'host number' , 'internal port addr' , 'bridge_name'), 'switch' ]
"""  



#  ---------------------- nodes dict ------------------   
"""
Keys: 
contr_addr = controller address for the switch (default none)
region = region name (defualt TR-EDGE-1)
flavor = flavor name (default m1.tiny)
image = image name   (default image-3.0.1)
bridge_name = bridge name for that switch
- internal ip, when specified, it will add an internal ip with the name (tuple at index 0) 
  and address (tuple at index 1). Normally an internal ip is not allocated to a switch

// they can all be left blank

:%s/CORE/CORE/g
"""


nodes = {}
nodes["sw1"] = {'contr_addr':'10.12.11.26:6633', 'region':'CORE', 'flavor': 'm1.small', 'bridge_name': 'sw1_br', 'int_ip':('p1', '192.168.200.18')}
nodes["sw2"] = {'contr_addr':'10.12.11.26:6633', 'region':'CORE', 'flavor': 'm1.small'}
nodes["sw3"] = {'contr_addr':'10.12.11.26:6633', 'region':'CORE', 'flavor': 'm1.small', 'bridge_name': 'sw3_br'}
nodes["h1"] = {'region':'CORE', 'flavor': 'm1.tiny'}
nodes["h2"] = {'region':'CORE', 'flavor': 'm1.tiny'}
nodes["h3"] = {'region':'CORE', 'flavor': 'm1.tiny'}
nodes["h4"] = {'region':'CORE', 'flavor': 'm1.tiny'}

# Do not connect two Vxlans to the same switch pairings while running a simple switch controller
topology = {}
topology["sw1"] = [('h1', '192.168.200.10', 'h1_br'), ('h4', '192.168.200.13')]
topology["sw2"] = ['sw1', ('h2', '192.168.200.11')]
topology["sw3"] = ['sw2', ('h3','192.168.200.12')]



