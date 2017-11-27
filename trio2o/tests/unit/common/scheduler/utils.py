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

from oslo_utils import timeutils
from oslo_utils import uuidutils

from trio2o.db import api as db_api


def create_pod(context, pod_name, az_name, create_time=timeutils.utcnow()):
    # create a pod for test use.
    pod_dict = {'pod_id': uuidutils.generate_uuid(),
                'pod_name': pod_name, 'az_name': az_name,
                'is_under_maintenance': False,
                'create_time': create_time}
    pod = db_api.create_pod(context, pod_dict)
    return pod


def create_pod_affinity_tag(context, pod_id, **tag_dict):
    pod_tag_dict = {}
    for key, value in tag_dict.items():
        pod_tag_dict['key'] = key
        pod_tag_dict['value'] = value
        pod_tag_dict['affinity_tag_id'] = uuidutils.generate_uuid()
        pod_tag_dict['pod_id'] = pod_id
        db_api.create_pod_affinity_tag(context, pod_tag_dict)


def create_pod_state_for_pod(context, pod_id, times=1):
    pod_state_dict = {
        'pod_state_id': uuidutils.generate_uuid(),
        'pod_id': pod_id,
        'count': 1 * times,
        'vcpus': 4 * times,
        'vcpus_used': 0,
        'memory_mb': 1024 * times,
        'memory_mb_used': 0,
        'local_gb': 4 * times,
        'local_gb_used': 0,
        'free_ram_mb': 1024 * times,
        'free_disk_gb': 4 * times,
        'current_workload': 1 * times,
        'running_vms': 1 * times,
        'disk_available_least': 4 * times,
    }
    pod_state = db_api.create_pod_state(context, pod_state_dict)
    return pod_state
