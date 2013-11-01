import sys
import time
import keystoneclient.v2_0.client as keystoneclient
import novaclient.v1_1.client as novaclient
import neutronclient.v2_0.client as neutronclient
from credentials import *

'''
    Creates a network and a COUNT of instances
    using the user / project configured in stackrc file 
'''

INSTANCE_NAME = 'fiva'
NETWORK_NAME='route-66'
INSTANCE_COUNT = 3

kcreds = get_keystone_creds()

print "Connecting to keystone"
keystone = keystoneclient.Client(**kcreds)
tokenlen=len(keystone.auth_token)
print keystone.auth_token[0:20] + "..." + keystone.auth_token[tokenlen-20:tokenlen]

ncreds = get_nova_creds()
nova = novaclient.Client(**ncreds)

flavors = nova.flavors.list(is_public=True)
print flavors

images = nova.images.list(detailed=False)
print images 

# get networks from quantum
print "Find or create network..."
network_url = keystone.service_catalog.url_for(service_type='network')
neutron = neutronclient.Client(endpoint_url=network_url, token=keystone.auth_token)
networks = neutron.list_networks()['networks']
print "Networks: "
print [(nw['name'],nw['id'])for nw in networks]

net = None
net_id = None
networks =  neutron.list_networks(name="route-66")['networks']
if len(networks)>0 and networks[0]['name'] == NETWORK_NAME : 
    net_id = networks[0]['id']
    print "Network found ", NETWORK_NAME, net_id
else:
    net = neutron.create_network({'network': 
              {'name': NETWORK_NAME,'admin_state_up': True} })
    print "Created network ", net
    net_id = net['network']['id']
    sub = neutron.create_subnet({'subnet': {
              'name': 'subnet',
              'network_id': net_id,
              'ip_version': 4,
              'cidr': '10.0.33.0/24'
              } 
          })
    print "Created subnet ", sub

print "List instances: "
# check what we get so far for instances
instances = nova.servers.list()

for instance in instances:
    print 'name: ', instance.name
    print 'host id: ', instance.hostId


print "Creating instances: "
instance = nova.servers.create(INSTANCE_NAME, images[0], flavors[0]
                # The actual number will be based on the quota. 
                # see http://www.gossamer-threads.com/lists/openstack/dev/17629
                ,min_count=1, max_count=INSTANCE_COUNT
                # if nics not specified, will connect to all project networks
                ,nics=[{'net-id': net_id}]
          )

# Poll at 5 second intervals, until the status is no longer 'BUILD'
status = instance.status
sys.stdout.write('Building...')
while status == 'BUILD':
    time.sleep(1)
    sys.stdout.write(".")
    sys.stdout.flush()
    # Retrieve the instance again so the status field updates
    instance = nova.servers.get(instance.id)
    status = instance.status

print "status: %s" % status
