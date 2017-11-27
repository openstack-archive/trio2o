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


class AllPodFilter(base_filters.BasePodFilter):
    """Returns all available pods."""

    def is_pod_passed(self, context, pod, request_spec):
        # If the pod is under maintenance, then it will pass the filter.
        return not pod['is_under_maintenance']
