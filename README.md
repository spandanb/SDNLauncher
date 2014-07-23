# SDN Launcher

In this work, we will utilize the SAVI testbed alongside a software 
defined switch (OpenVSwitch) to dynamically create network topologies 
specified by the user. Similar to mininet, the users will be able to 
specify the number of hosts and switches and specify how they want them 
to be connected. 

The goal is to create a layer 2 or a layer 3 network and linking up the 
nodes as defined by the user topology. For this purpose, we use SAVI TB
and VXLAN tunneling protocol to create arbitrary overlay networks. 

These overlay networks could be used in variety of applications from 
deploying a large scale OpenFlow network in order to test a SDN controller
and application to running a large scale distributed application on a 
desired topology.

## Usage

### Credentials
    
Make a copy of the config.py.example file and call it config.py. <br>
Open the file and specify your savi username and password by changing the value of the variables **user** and **password** <br>
E.x. <br>
**user = "your_username"**<br>
**password = "your_password"**<br>


Specify your **keypair name** and **private key path** by changing the 
        values of variables **private_key_file** and **key_name**.


Optionally, change the tenant and region name.


Save and close the file.

### Specifying Topology
    
    1. Modify the topology file.
    2. Specify the controller IP address and port number for the **cont_addr**
        variable as a colon separated string.
    3. Specify all the hosts and switches in the nodes dictionary.
        For the switch, specify the region, the flavor, the bridge name, the internal ip.
        For the host, specify the region and flavor.
        Additionally, the region and flavor fields can be left blank, 
        and the default values will be used. 

```python 
nodes = {}
nodes["sw1"] = {'contr_addr': contr_addr, 'region':'CORE', 'flavor': 'm1.small', 'bridge_name': 'sw1_br', 'int_ip':('p1', '192.168.200.18')}
nodes["sw2"] = {'contr_addr': contr_addr, 'region':'CORE', 'flavor': 'm1.small'}
nodes["sw3"] = {'contr_addr': contr_addr, 'region':'CORE', 'flavor': 'm1.small', 'bridge_name': 'sw3_br'}
nodes["h1"] = {'region':'CORE', 'flavor': 'm1.tiny'}
nodes["h2"] = {'region':'CORE', 'flavor': 'm1.tiny'}
nodes["h3"] = {'region':'CORE', 'flavor': 'm1.tiny'}
nodes["h4"] = {'region':'CORE', 'flavor': 'm1.tiny'}
```
    4. Specify the connections between the hosts and switches.
        E.x.

```python
topology["sw1"] = [('h1', '192.168.200.10', 'h1_br'), ('h4', '192.168.200.13')]
topology["sw2"] = ['sw1', ('h2', '192.168.200.11')]
topology["sw3"] = ['sw2', ('h3','192.168.200.12')]
```

    5. Test by SSHing to a host and pinging another host on 
        its private IP address (i.e. its 192.168... address) 
        

### Cleaning Up

To cleanup, call the cleanup script: **cleanup.py**.

##Contact
Khashayar Hossein Zadeh, 
Email <k.hosseinzadeh@mail.utoronto.ca>

Hadi Bannazadeh
Email <hadi.bannazadeh@utoronto.ca>
