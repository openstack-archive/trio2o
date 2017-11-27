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

from oslo_config import cfg
from oslo_log import log as logging
import random

from trio2o.common.scheduler import driver
from trio2o.db import api as db_api

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class FilterScheduler(driver.Scheduler):

    def __init__(self, *args, **kwargs):
        super(FilterScheduler, self).__init__(*args, **kwargs)

    def select_destination(self, context, spec_obj):
        # 1, we use tenant filter to search all bound pods, if the pod could
        # meet the need, then we directly provision the resource in this pod
        # and no need to create new binding relationship with tenant.
        self.pod_manager.enable_tenant_filter()
        has_binding = True
        if not isinstance(spec_obj, dict):
            spec_obj = spec_obj.to_dict()
        project_id = spec_obj['project_id']
        ret_pod = self._schedule(context, spec_obj, has_binding)

        # 2, we remove tenant filter if first step fails to find a pod or the
        # resources in this pod have been used up, then we need to add these
        # bound pods to ignore_pods to get rid of filtering them again.
        if not ret_pod:
            has_binding = False
            pods = self.pod_manager.get_current_bound_pods(context, project_id)
            for pod in pods:
                spec_obj['ignore_pods'] = pod['pod_name']
            self.pod_manager.disable_tenant_filter()
            ret_pod = self._schedule(context, spec_obj, has_binding)
        if ret_pod:
            return ret_pod
        else:
            return None

    def _get_sorted_pods(self, context, spec_obj, pods):
        filtered_pods = self.pod_manager.get_filtered_pods(context, pods,
                                                           spec_obj)
        LOG.debug("Filtered %(pods)s", {'pods': filtered_pods})
        if not filtered_pods:
            return []

        pod_state_objs = self.pod_manager.get_all_pod_states(context,
                                                             filtered_pods)
        weighed_pods = self.pod_manager.get_weighed_pods(pod_state_objs, {})

        if CONF.filter_scheduler.shuffle_best_same_weighed_pods:
            # Randomize best pods, relying on weighed_pods
            # being already sorted by weight in descending order.
            # This decreases possible contention and rescheduling attempts
            # when there is a large number of pods having the same best
            # weight, especially so when pod_subset_size is 1 (default)
            best_pods = [w for w in weighed_pods
                         if w.weight == weighed_pods[0].weight]
            random.shuffle(best_pods)
            weighed_pods = best_pods + weighed_pods[len(best_pods):]
        # Strip off the WeighedPod wrapper class...
        weighed_pods = [p.obj for p in weighed_pods]

        LOG.debug("Weighed %(pods)s", {'pods': weighed_pods})

        # We randomize the first element in the returned list to alleviate
        # congestion where the same pod is consistently selected among
        # numerous potential pods for similar request specs.
        pod_subset_size = CONF.filter_scheduler.pod_subset_size
        if pod_subset_size < len(weighed_pods):
            weighed_subset = weighed_pods[0:pod_subset_size]
        else:
            weighed_subset = weighed_pods
        chosen_pod = random.choice(weighed_subset)
        weighed_pods.remove(chosen_pod)
        return [chosen_pod] + weighed_pods

    def _schedule(self, context, spec_obj, has_binding):
        pods = db_api.list_pods(context)
        # NOTICE: here it's no need to claim resources from pod, after the
        # vm runs successfully, the vm scheduler in dedicated host will
        # claim the resource according to the flavor. The pod state only
        # pulls statistics information from all hypervisors, so after resource
        # information is updated in host, the pod state is updated as well
        # when we create vm next time.
        pods = self._get_sorted_pods(context, spec_obj, pods)
        ret_pod = None
        if len(pods) > 0:
            pod = db_api.get_pod_by_pod_id(context,
                                           pods[0]['pod_id'])
            ret_pod = pod
        return ret_pod
