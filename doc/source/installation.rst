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

      openstack --os-region-name=RegionOne token issue

- 9 Create pod instances for the Trio2o to manage the mapping between
  availability zone and OpenStack instances, the "$token" is obtained in the
  step 7::

      curl -X POST http://127.0.0.1:19999/v1.0/pods -H "Content-Type: application/json" \
          -H "X-Auth-Token: $token" -d '{"pod": {"pod_name":  "RegionOne"}}'

      curl -X POST http://127.0.0.1:19999/v1.0/pods -H "Content-Type: application/json" \
          -H "X-Auth-Token: $token" -d '{"pod": {"pod_name":  "Pod1", "az_name": "az1"}}'

  Pay attention to "pod_name" parameter we specify when creating pod. Pod name
  should exactly match the region name registered in Keystone. In the above
  commands, we create pods named "RegionOne" and "Pod1".

- 10 Create necessary resources in local Neutron server::

     neutron --os-region-name=Pod1 net-create net1
     neutron --os-region-name=Pod1 subnet-create net1 10.0.0.0/24

  Please note that the net1 ID will be used in later step to boot VM.

- 11 Get image ID and flavor ID which will be used in VM booting::

     glance --os-region-name=RegionOne image-list
     nova --os-region-name=RegionOne flavor-create test 1 1024 10 1
     nova --os-region-name=RegionOne flavor-list

- 12 Boot a virtual machine::

     nova --os-region-name=RegionOne boot --flavor 1 --image $image_id --nic net-id=$net_id vm1

- 13 Verify the VM is connected to the net1::

     neutron --os-region-name=Pod1 port-list
     nova --os-region-name=RegionOne list

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

