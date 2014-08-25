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
    
    1. Make a copy of the config.py.example file and call it config.py.
    2. Open the file and specify your savi username and password by changing the value of the variables **user** and **password** 
         E.x. 
            user = "your_username"
            password = "your_password"


    3. Specify your **keypair name** and **private key path** by changing the 
        values of variables **private_key_file** and **key_name**.


    4. Optionally, change the default image name, tenant and region name.


    5. Save and close the file.

### OF Controller VM

Create a VM that can host OF controller. Example below shows how to get a VM that has all major open-source controllers (Ryu, ODL, Floodlight, etc). This image is built on SDN tutorial image from http://sdnhub.org/tutorials/sdn-tutorial-vm/. (image name in SAVI TB: SDN-image):

savi-run-server m1.small SDN-image key sec-group vm-name

after VM boots up, please take note of VM IP address and use it as the controller IP address in next step.

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
nodes["h1"] = {'region':'CORE', 'flavor': 'm1.tiny'}
nodes["h2"] = {'region':'CORE', 'flavor': 'm1.tiny'}
```
    4. Specify the connections between the hosts and switches.
        E.x.

```python
topology["sw1"] = [('h1', '192.168.200.10', 'h1_br'), ('h2', '192.168.200.11')]
```

### Running SDN Launcher
To run the SDN Launch, run the following command, in this directory:
```python
./SDNLauncher
```

Another option is to run two scripts separately; one to boot up nodes and one to setup topology:

To setup nodes:

```python
./SetupNodes.py
```

To (re)setup topology:

```python
./SetupTopology.py
```

To get infomation:

```python
./GetInformation.py
```

###Running OF controller
ssh to your controller VM and run OF controller.
For instance: 

```python
cd ~/ryu; ryu-manager ryu.app.simple_switch.py
```

###Testing
 Test by SSHing to a host and pinging another host on 
        its private IP address (i.e. its 192.168... address) 
        
###Cleaning Up

To cleanup, call the cleanup script: **cleanup.py VM_prefix**.

##Contact
Khashayar Hossein Zadeh, 
Email <k.hosseinzadeh@mail.utoronto.ca>

Hadi Bannazadeh
Email <hadi.bannazadeh@utoronto.ca>
