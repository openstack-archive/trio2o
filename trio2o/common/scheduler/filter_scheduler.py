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

filter_scheduler_group = cfg.OptGroup(name="filter_scheduler",
                                      title="Filter scheduler options")

filter_scheduler_opts = [
    cfg.FloatOpt("ram_weight_multiplier",
                 default=1.0,
                 help="Ram weight multipler ratio"),
    cfg.FloatOpt("disk_weight_multiplier",
                 default=1.0,
                 help="Disk weight multipler ratio"),
    cfg.FloatOpt("vcpu_weight_multiplier",
                 default=1.0,
                 help="VCPU weight multipler ratio"),
    cfg.FloatOpt("workload_weight_multiplier",
                 default=1.0,
                 help="Workload weight multipler ratio"),
    cfg.IntOpt("pod_subset_size",
               default=1,
               min=1,
               help="""
Size of subset of best pods selected by scheduler.

New instances will be scheduled on a pod chosen randomly from a subset of the
N best pods, where N is the value set by this option.

Setting this to a value greater than 1 will reduce the chance that multiple
scheduler processes handling similar requests will select the same pod,
creating a potential race condition. By selecting a pod randomly from the N
pods that best fit the request, the chance of a conflict is reduced. However,
the higher you set this value, the less optimal the chosen pod may be for a
given request.

This option is only used by the FilterScheduler and its subclasses; if you use
a different scheduler, this option has no effect.

Possible values:

* An integer, where the integer corresponds to the size of a pod subset. Any
  integer is valid, although any value less than 1 will be treated as 1
"""),
    cfg.MultiStrOpt("available_filters",
                    default=["trio2o.common.scheduler.filters.all_filters"],
                    help="""
Filters that the scheduler can use.

An unordered list of the filter classes the tricircle scheduler may apply.
Only the filters specified in the 'enabled_filters' option will be used, but
any filter appearing in that option must also be included in this list.

By default, this is set to all filters that are included with tricircle.

Possible values:

* A list of zero or more strings, where each string corresponds to the name of
  a filter that may be used for selecting a pod

Related options:

* enabled_filters
"""),
    cfg.ListOpt("enabled_filters",
                default=[
                    "AvailabilityZoneFilter",
                    "AllPodFilter",
                    "BottomPodFilter",
                    "PodAffinityTagFilter",
                    "CreateTimeFilter",
                    "DiskFilter",
                    "RamFilter",
                ],
                help="""
Filters that the scheduler will use.

An ordered list of filter class names that will be used for filtering
pods. These filters will be applied in the order they are listed so
place your most restrictive filters first to make the filtering process more
efficient.

This option is only used by the FilterScheduler and its subclasses; if you use
a different scheduler, this option has no effect.

Possible values:

* A list of zero or more strings, where each string corresponds to the name of
  a filter to be used for selecting a pod

Related options:

* All of the filters in this option *must* be present in the
  'available_filters' option, or a SchedulerPodFilterNotFound
  exception will be raised.
"""),
    cfg.ListOpt("weight_classes",
                default=["trio2o.common.scheduler.weights.all_weighers"],
                help="""
Weighers that the scheduler will use.

Only pods which pass the filters are weighed. The weight for any pod starts
at 0, and the weighers order these pods by adding to or subtracting from the
weight assigned by the previous weigher. Weights may become negative. An
instance will be scheduled to one of the N most-weighted pods, where N is
'pod_subset_size'.

By default, this is set to all weighers that are included with Tricircle.

This option is only used by the FilterScheduler and its subclasses; if you use
a different scheduler, this option has no effect.

Possible values:

* A list of zero or more strings, where each string corresponds to the name of
  a weigher that will be used for selecting a pod
"""),
    cfg.BoolOpt(
        "shuffle_best_same_weighed_pods",
        default=False,
        help="""
Enable spreading the instances between pods with the same best weight.

Enabling it is beneficial for cases when pod_subset_size is 1
(default), but there is a large number of pods with same maximal weight.
This scenario is common in Ironic deployments where there are typically many
baremetal nodes with identical weights returned to the scheduler.
In such case enabling this option will reduce contention and chances for
rescheduling events.
At the same time it will make the instance packing (even in unweighed case)
less dense.
"""),
]

cfg.CONF.register_group(filter_scheduler_group)
cfg.CONF.register_opts(filter_scheduler_opts, group=filter_scheduler_group)

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
            return ret_pod, ret_pod['pod_name']
        else:
            return None, None

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
        project_id = spec_obj['project_id']
        pods = db_api.list_pods(context)
        ret_pod = None
        # NOTICE: here it's no need to claim resources from pod, after the
        # vm runs successfully, the vm scheduler in dedicated host will
        # claim the resource according to the flavor. The pod state only
        # pulls statistics information from all hypervisors, so after resource
        # information is updated in host, the pod state is updated as well
        # when we create vm next time.
        pods = self._get_sorted_pods(context, spec_obj, pods)
        if len(pods) > 0:
            pod = db_api.get_pod_by_pod_id(context,
                                           pods[0]['pod_id'])
            # If the tenant current binds with a pod, then we update
            # the binding relationship, or else we create new binding
            if has_binding:
                is_successful = self.pod_manager.update_binding(
                    context,
                    project_id,
                    pod
                )
            else:
                is_successful = self.pod_manager.create_binding(
                    context, project_id, pod['pod_id'])
            if is_successful:
                ret_pod = pod
            else:
                ret_pod = None
        return ret_pod
