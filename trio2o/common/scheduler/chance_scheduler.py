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

from oslo_log import log as logging
import random

from trio2o.common.scheduler import driver
from trio2o.db import api as db_api

LOG = logging.getLogger(__name__)


class ChanceScheduler(driver.Scheduler):
    """Implements Scheduler as a random pod selector."""

    def __init__(self, *args, **kwargs):
        super(ChanceScheduler, self).__init__(*args, **kwargs)

    def select_destination(self, context, spec_obj):
        """Selects random destinations. Returns pod object."""
        if not isinstance(spec_obj, dict):
            spec_obj = spec_obj.to_dict()
        ret_pod = self._schedule(context, spec_obj)

        if ret_pod:
            return ret_pod
        else:
            return None

    def _filter_pods(self, ctx, pods, spec_obj):
        """Filter a list of pods based on RequestSpec."""
        ignore_pods = spec_obj['ignore_pods']

        pods = [pod for pod in pods if pod['az_name'] != '']
        pods = [pod for pod in pods if not pod['is_under_maintenance']]
        pods = [pod for pod in pods if pod['pod_name'] not in ignore_pods]
        pods = [pod for pod in pods if self._affinity_tag_filter(ctx, pod,
                                                                 spec_obj)]
        return pods

    @staticmethod
    def _affinity_tag_filter(context, pod, request_spec):
        # If the pod has asked resource affinity tag, then it will pass the
        # filter.
        flag = True

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

    def _schedule(self, context, spec_obj):
        """Picks a pod that is up at random."""
        pods = db_api.list_pods(context)
        pods = self._filter_pods(context, pods, spec_obj)

        ret_pod = None
        if pods:
            # Currently no alternate pods are returned, we only select one
            # proper pod to build vm or container.
            ret_pod = random.sample(pods, 1)[0]

        return ret_pod
