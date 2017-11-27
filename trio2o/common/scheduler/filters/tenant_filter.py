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

from trio2o.common.scheduler import filters
from trio2o.db import api as db_api


class TenantFilter(filters.BasePodFilter):
    """Returns all the pods that have been bound with the tenant."""

    def is_pod_passed(self, context, pod, request_spec):
        flag = True

        if not isinstance(request_spec, dict):
            request_spec = request_spec.to_dict()
        project_id = request_spec['project_id']
        filter_binding = [{'key': 'tenant_id', 'comparator': 'eq',
                           'value': project_id},
                          {'key': 'pod_id', 'comparator': 'eq',
                           'value': pod['pod_id']}
                          ]
        current_binding = db_api.get_pod_binding_by_tenant_id(context,
                                                              filter_binding)
        if not current_binding:
            flag = False
        return flag
