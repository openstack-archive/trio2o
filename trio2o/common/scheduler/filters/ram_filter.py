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

from trio2o.common.scheduler.filters import base_filters
from trio2o.db import api as db_api


class RamFilter(base_filters.BasePodFilter):
    """Returns all available pods that have as much available memory space

     as asked.
     """
    def is_pod_passed(self, context, pod, request_spec):
        flag = True
        pod_state = db_api.get_pod_state_by_pod_id(context, pod['pod_id'])[0]
        free_ram_space = pod_state['memory_mb'] - pod_state['memory_mb_used']

        if not isinstance(request_spec, dict):
            request_spec = request_spec.to_dict()
        req_ram_space = request_spec['memory_mb']
        if req_ram_space is not None and req_ram_space > free_ram_space:
            flag = False

        return flag
