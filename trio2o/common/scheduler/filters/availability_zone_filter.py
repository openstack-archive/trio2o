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


class AvailabilityZoneFilter(base_filters.BasePodFilter):
    """Returns all available pods in specified availability zone."""

    def is_pod_passed(self, context, pod, request_spec):
        # If the pod locates in specified availability zone, then it will pass
        # the filter.
        flag = True

        if not isinstance(request_spec, dict):
            request_spec = request_spec.to_dict()
        req_az_name = request_spec['az_name']
        if req_az_name is not None and req_az_name != pod['az_name']:
            flag = False
        return flag
