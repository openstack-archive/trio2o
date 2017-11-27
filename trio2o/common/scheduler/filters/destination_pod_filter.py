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


class DestinationPodFilter(filters.BasePodFilter):
    """If the pod is exactly the one user targets at, it returns True."""

    def is_pod_passed(self, context, pod, request_spec):
        flag = True
        pod_name = pod['pod_name']

        if not isinstance(request_spec, dict):
            request_spec = request_spec.to_dict()
        target_pod_name = request_spec['requested_destination']

        if target_pod_name is not None and pod_name != target_pod_name:
            flag = False
        return flag
