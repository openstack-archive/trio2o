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


class PodAffinityTagFilter(base_filters.BasePodFilter):
    """Returns pod with asked affinity tag."""
    def is_pod_passed(self, context, pod, request_spec):
        # If the pod has asked resource affinity tag, then it will pass the
        # filter.
        flag = True

        if not isinstance(request_spec, dict):
            request_spec = request_spec.to_dict()
        req_affinity_tags = request_spec['affinity_tags']

        # collect key-value pairs in pod affinity tags
        affinity_tag_filter = [{'key': 'pod_id',
                                'comparator': 'eq',
                                'value': pod['pod_id']}]
        tags = db_api.list_pod_affinity_tag(context, affinity_tag_filter)
        all_affinity_tags = {}
        for tag in tags:
            all_affinity_tags[tag['key']] = tag['value']

        for key, value in req_affinity_tags.items():
            value_in_pod = all_affinity_tags.get(key, None)
            if value_in_pod is None or value_in_pod != value:
                flag = False
                break
        return flag
