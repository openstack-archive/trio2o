#!/bin/bash -xe

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# This script is executed inside post_test_hook function in devstack gate.

export DEST=$BASE/new
export DEVSTACK_DIR=$DEST/devstack
export TRIO2O_DIR=$DEST/trio2o
export TRIO2O_DEVSTACK_PLUGIN_DIR=$TRIO2O_DIR/devstack
export TRIO2O_TEMPEST_PLUGIN_DIR=$TRIO2O_DIR/trio2o/tempestplugin
export TEMPEST_DIR=$DEST/tempest
export TEMPEST_CONF=$TEMPEST_DIR/etc/tempest.conf

# use admin role to create Trio2o top Pod and Pod1
source $DEVSTACK_DIR/openrc admin admin

# unset OS_REGION_NAME

# mytoken=$(openstack --os-region-name=RegionOne token issue -f value -c id)
mytoken=$(openstack token issue -f value -c id)
echo $mytoken

curl -X POST http://127.0.0.1:19996/v1.0/pods \
    -H "Content-Type: application/json" \
    -H "X-Auth-Token: $mytoken" -d '{"pod": {"pod_name":  "RegionOne"}}'

curl -X POST http://127.0.0.1:19996/v1.0/pods \
    -H "Content-Type: application/json" \
    -H "X-Auth-Token: $mytoken" \
    -d '{"pod": {"pod_name":  "Pod1", "az_name": "az1"}}'

# the usage of "nova flavor-create":
# nova flavor-create [--ephemeral <ephemeral>] [--swap <swap>]
#                    [--rxtx-factor <factor>] [--is-public <is-public>]
#                    <name> <id> <ram> <disk> <vcpus>
# the following command is to create a flavor wih name='test',
# id=1, ram=1024MB, disk=10GB, vcpu=1
# nova --os-region-name=RegionOne flavor-create test 1 1024 10 1
# image_id=$(glance --os-region-name=RegionOne image-list | awk 'NR==4 {print $2}')
nova flavor-create test 1 1024 10 1
image_id=$(glance image-list | awk 'NR==4 {print $2}')

# preparation for the tests
cd $TEMPEST_DIR
if [ -d .testrepository ]; then
  sudo rm -r .testrepository
fi

sudo chown -R $USER:stack $DEST/tempest
# sudo chown -R $USER:stack $BASE/data/tempest

# change the tempest configruation to test Trio2o
env | grep OS_

# import functions needed for the below workaround
source $DEVSTACK_DIR/functions

# designate is a good example how to config TEMPEST_CONF
iniset $TEMPEST_CONF auth admin_username ${ADMIN_USERNAME:-"admin"}
iniset $TEMPEST_CONF auth admin_project_name admin
iniset $TEMPEST_CONF auth admin_password $OS_PASSWORD
iniset $TEMPEST_CONF auth admin_domain_name default
iniset $TEMPEST_CONF identity auth_version v3
iniset $TEMPEST_CONF identity uri_v3 http://$SERVICE_HOST/identity/v3
iniset $TEMPEST_CONF identity uri $OS_AUTH_URL
iniset $TEMPEST_CONF identity-feature-enabled api_v3 True

iniset $TEMPEST_CONF compute region RegionOne
iniset $TEMPEST_CONF compute image_ref $image_id
iniset $TEMPEST_CONF compute image_ref_alt $image_id

iniset $TEMPEST_CONF volume region RegionOne
iniset $TEMPEST_CONF volume catalog_type volumev2
iniset $TEMPEST_CONF volume endpoint_type publicURL
iniset $TEMPEST_CONF volume-feature-enabled api_v1 false

iniset $TEMPEST_CONF validation connect_method fixed

# Run the Compute Tempest tests
cd $TRIO2O_TEMPEST_PLUGIN_DIR
sudo BASE=$BASE ./tempest_compute.sh

# Run the Volume Tempest tests
cd $TRIO2O_TEMPEST_PLUGIN_DIR
sudo BASE=$BASE ./tempest_volume.sh

# Run the Scenario Tempest tests
# cd $TRIO2O_TEMPEST_PLUGIN_DIR
# sudo BASE=$BASE ./tempest_scenario.sh
