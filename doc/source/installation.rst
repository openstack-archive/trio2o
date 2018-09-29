==================================
Trio2o installation with DevStack
==================================

Now the Trio2o can be played with all-in-one single node DevStack. For
the resource requirement to setup single node DevStack, please refer
to `All-In-One Single Machine <http://docs.openstack.org/developer/devstack/guides/single-machine.html>`_ for
installing DevStack in physical machine
or `All-In-One Single VM <http://docs.openstack.org/developer/devstack/guides/single-vm.html>`_ for
installing DevStack in virtual machine.

- 1 Install DevStack. Please refer to `DevStack document
  <http://docs.openstack.org/developer/devstack/>`_
  on how to install DevStack into single VM or physcial machine

- 2 In DevStack folder, create a file local.conf, and copy the content of
  https://github.com/openstack/trio2o/blob/master/devstack/local.conf.sample
  to local.conf, change password in the file if needed.

- 3 In local.conf, change HOST_IP to the host's IP address where the Trio2o
  will be installed to, for example::

    HOST_IP=162.3.124.203

- 4 Run DevStack. In DevStack folder, run::

    ./stack.sh

- 5 After DevStack successfully starts, we need to create environment variables for
  the user (admin user as example in this document). In DevStack folder::

      source openrc admin admin

- 6 Unset the region name environment variable, so that the command can be issued to
  specified region in following commands as needed::

      unset OS_REGION_NAME

- 7 Check if services have been correctly registered. Run::

      openstack --os-region-name=RegionOne endpoint list

  you should get output looks like as following::

        +----------------------------------+-----------+--------------+----------------+
        | ID                               | Region    | Service Name | Service Type   |
        +----------------------------------+-----------+--------------+----------------+
        | e8a1f1a333334106909e05037db3fbf6 | Pod1      | neutron      | network        |
        | 72c02a11856a4814a84b60ff72e0028d | Pod1      | cinderv2     | volumev2       |
        | a26cff63563a480eaba334185a7f2cec | Pod1      | nova         | compute        |
        | f90d97f8959948088ab58bc143ecb011 | RegionOne | cinderv3     | volumev3       |
        | ed1af45af0d8459ea409e5c0dd0aadba | RegionOne | cinder       | volume         |
        | ae6024a582534c21aee0c6d7fa5b90fb | RegionOne | nova         | compute        |
        | c75ab09edc874bb781b0d376cec74623 | RegionOne | cinderv2     | volumev2       |
        | 80ce6a2d12aa43fab693f4e619670d97 | RegionOne | trio2o       | Cascading      |
        | 11a4b451da1a4db6ae14b0aa282f9ba6 | RegionOne | nova_legacy  | compute_legacy |
        | 546a8abf29244223bc9d5dd4960553a7 | RegionOne | glance       | image          |
        | 0e9c9343b50e4b7080b25f4e297f79d3 | RegionOne | keystone     | identity       |
        +----------------------------------+-----------+--------------+----------------+

  "RegionOne" is the region where the Trio2o Admin API(ID is
  80ce6a2d12aa43fab693f4e619670d97 in the above list), Nova API gateway(
  ID is ae6024a582534c21aee0c6d7fa5b90fb) and Cinder API gateway( ID is
  c75ab09edc874bb781b0d376cec74623) are running in. "Pod1" is the normal
  bottom OpenStack region which includes Nova, Cinder, Neutron.

- 8 Get token for the later commands. Run::

      token=$(openstack --os-region-name=RegionOne token issue | awk 'NR==5 {print $4}')

- 9 GET pod instances for the Trio2o to manage the mapping between
  availability zone and OpenStack instances, the "$token" is obtained in the
  step 7::

      curl -X GET  http://127.0.0.1:19996/v1.0/pods -H "Content-Type: application/json" \
          -H "X-Auth-Token: $token"

  if return empty results, use commands following::

      curl -X POST http://127.0.0.1:19996/v1.0/pods -H "Content-Type: application/json" \
          -H "X-Auth-Token: $token" -d '{"pod": {"pod_name":  "RegionOne"}}'

      curl -X POST http://127.0.0.1:19996/v1.0/pods -H "Content-Type: application/json" \
          -H "X-Auth-Token: $token" -d '{"pod": {"pod_name":  "Pod1", "az_name": "az1"}}'

  Pay attention to "pod_name" parameter we specify when creating pod. Pod name
  should exactly match the region name registered in Keystone. In the above
  commands, we create pods named "RegionOne" and "Pod1".

- 10 Create necessary resources in Neutron server::

     neutron --os-region-name=RegionOne net-create net1
     neutron --os-region-name=RegionOne subnet-create net1 10.0.0.0/24

  Please note that the net1 ID will be used in later step to boot VM.

- 11 Get image ID and flavor ID which will be used in VM booting::

     glance --os-region-name=RegionOne image-list
     nova --os-region-name=RegionOne flavor-create test 1 1024 10 1
     nova --os-region-name=RegionOne flavor-list

- 12 Boot a virtual machine::

     nova --os-region-name=RegionOne boot --flavor 1 --image $image_id --nic net-id=$net_id vm1

- 13 Verify the VM is connected to the net1::

     nova --os-region-name=RegionOne list
     nova --os-region-name=Pod1 list
     neutron --os-region-name=RegionOne port-list

- 14 Create, list, show and delete volume::

     cinder --os-region-name=RegionOne create --availability-zone=az1 1
     cinder --os-region-name=RegionOne list
     cinder --os-region-name=RegionOne show $volume_id
     cinder --os-region-name=RegionOne delete $volume_id
     cinder --os-region-name=RegionOne list

- 15 Using --debug to make sure the commands are issued to Nova API gateway
  or Cinder API gateway::

     nova --debug --os-region-name=RegionOne list
     cinder --debug --os-region-name=RegionOne list

  The nova command should be sent to http://162.3.124.203:19998/ and cinder
  command to http://162.3.124.203:19997/

========================================
Add another pod to Trio2o with DevStack
========================================
- 1 Prepare another node(suppose it's node-2), be sure the node is ping-able
  from the node(suppose it's node-1) where the Trio2o is installed and running.
  For the resource requirement to setup another node DevStack, please refer
  to `All-In-One Single Machine <http://docs.openstack.org/developer/devstack/guides/single-machine.html>`_ for
  installing DevStack in physical machine
  or `All-In-One Single VM <http://docs.openstack.org/developer/devstack/guides/single-vm.html>`_ for
  installing DevStack in virtual machine.

- 2 Install DevStack in node-2. Please refer to `DevStack document
  <http://docs.openstack.org/developer/devstack/>`_
  on how to install DevStack into single VM or physcial machine

- 3 In node-2 DevStack folder, create a file local.conf, and copy the
  content of https://github.com/openstack/trio2o/blob/master/devstack/local.conf.sample2
  to local.conf, change password in the file if needed.

- 4 In node-2 local.conf, change the REGION_NAME for the REGION_NAME is
  used as the region name if needed::

    REGION_NAME=Pod2

- 5 In node-2 local.conf, change following IP to the host's IP address of node-2,
  for example, if node-2's management interface IP address is 162.3.124.204::

    HOST_IP=162.3.124.204
    SERVICE_HOST=162.3.124.204

- 6 In node-2, the OpenStack will use the KeyStone which is running in
  node-1, so change the KEYSTONE_REGION_NAME and KEYSTONE host IP address
  to node-1 IP address accordingly::

    KEYSTONE_REGION_NAME=RegionOne
    KEYSTONE_SERVICE_HOST=162.3.124.203
    KEYSTONE_AUTH_HOST=162.3.124.203

- 7 In node-2, the OpenStack will use the Glance which is running in
  node-1, so change the GLANCE_SERVICE_HOST IP address to node-1 IP
  address accordingly::
    GLANCE_SERVICE_HOST=162.3.124.203

- 8 Run DevStack. In DevStack folder, run::

    ./stack.sh

- 9 After node-2 DevStack successfully starts, return to the noed-1. In
  node-1 DevStack folder::

      source openrc admin admin

- 10 Unset the region name environment variable in node-1, so that the command
  can be issued to specified region in following commands as needed::

      unset OS_REGION_NAME

- 11 Check if services in node-1 and node-2 have been correctly registered.
  Run::

      openstack --os-region-name=RegionOne endpoint list

  you should get output looks like as following::

        +----------------------------------+-----------+--------------+----------------+
        | ID                               | Region    | Service Name | Service Type   |
        +----------------------------------+-----------+--------------+----------------+
        | e09ca9acfa6341aa8f2671571c73db28 | RegionOne | glance       | image          |
        | 2730fbf212604687ada1f20b203fa0d7 | Pod2      | nova_legacy  | compute_legacy |
        | 7edd2273b0ae4bc68bbf714f561c2958 | Pod2      | cinder       | volume         |
        | b39c6e4d1be143d694f620b53b4a6015 | Pod2      | cinderv2     | volumev2       |
        | 9612c10655bb4fc994f3db4af72bfdac | Pod2      | nova         | compute        |
        | 6c28b4a76fa148578a12423362a5ade1 | RegionOne | trio2o       | Cascading      |
        | a1f439e8933d48e9891d238ad8e18bd5 | RegionOne | keystone     | identity       |
        | 452b249592d04f0b903ee24fa0dbb573 | RegionOne | nova         | compute        |
        | 30e7efc5e8f841f192cbea4da31ae5d5 | RegionOne | cinderv3     | volumev3       |
        | 63b88f4023cc44b59cfca53ad9606b85 | RegionOne | cinderv2     | volumev2       |
        | 653693d607934da7b7724c0cd1c49fb0 | Pod2      | neutron      | network        |
        | 3e3ccb71b8424958ad5def048077ddf8 | Pod1      | nova         | compute        |
        | d4615bce839f43f2a8856f3795df6833 | Pod1      | neutron      | network        |
        | fd2004b26b6847df87d1036c2363ed22 | RegionOne | cinder       | volume         |
        | 04ae8677ec704b779a1c00fa0eca2636 | Pod1      | cinderv2     | volumev2       |
        | e11be9f233d1434bbf8c4b8edf6a2f50 | RegionOne | nova_legacy  | compute_legacy |
        | d50e2dfbb87b43e98a5899eae4fd4d72 | Pod2      | cinderv3     | volumev3       |
        +----------------------------------+-----------+--------------+----------------+

  "RegionOne" is the region where the Trio2o Admin API(ID is
  6c28b4a76fa148578a12423362a5ade1 in the above list), Nova API gateway(
  ID is 452b249592d04f0b903ee24fa0dbb573) and Cinder API gateway(ID is
  63b88f4023cc44b59cfca53ad9606b85) are running in. "Pod1" is the normal
  bottom OpenStack region which includes Nova, Cinder, Neutron in node-1.
  "Pod2" is the normal bottom OpenStack region which includes Nova, Cinder,
  Neutron in node-2.

- 12 Get token for the later commands. Run::

      token=$(openstack --os-region-name=RegionOne token issue | awk 'NR==5 {print $4}')

- 13 Create Pod2 instances for the Trio2o to manage the mapping between
  availability zone and OpenStack instances, the "$token" is obtained in the
  step 11::

      curl -X POST http://127.0.0.1:19996/v1.0/pods -H "Content-Type: application/json" \
          -H "X-Auth-Token: $token" -d '{"pod": {"pod_name":  "Pod2", "az_name": "az2"}}'

  Pay attention to "pod_name" parameter we specify when creating pod. Pod name
  should exactly match the region name registered in Keystone. In the above
  commands, we create pod named "Pod2" in "az2".

- 14 Create necessary resources in local Neutron server::

     neutron --os-region-name=Pod2 net-create net2
     neutron --os-region-name=Pod2 subnet-create net2 10.0.0.0/24

  Please note that the net2 ID will be used in later step to boot VM.

- 15 Get image ID and flavor ID which will be used in VM booting, flavor
  should have been created in node-1 installation, if not, please create
  one::

     glance --os-region-name=RegionOne image-list
     nova --os-region-name=RegionOne flavor-create test 1 1024 10 1
     nova --os-region-name=RegionOne flavor-list

- 16 Boot a virtual machine in net2, replace $net-id to net2's ID::

     nova --os-region-name=RegionOne boot --availability-zone az2 --flavor 1 --image $image_id --nic net-id=$net_id vm2

- 17 Verify the VM is connected to the net2::

     neutron --os-region-name=Pod2 port-list
     nova --os-region-name=RegionOne list

- 18 Create, list, show and delete volume::

     cinder --os-region-name=RegionOne create --availability-zone=az2 1
     cinder --os-region-name=RegionOne list
     cinder --os-region-name=RegionOne show $volume_id
     cinder --os-region-name=RegionOne delete $volume_id
     cinder --os-region-name=RegionOne list

- 19 Using --debug to make sure the commands are issued to Nova API gateway
  or Cinder API gateway::
     nova --debug --os-region-name=RegionOne list
     cinder --debug --os-region-name=RegionOne list
  The nova command should be sent to http://127.0.0.1:19998/ and cinder
  command to http://127.0.0.1:19997/
