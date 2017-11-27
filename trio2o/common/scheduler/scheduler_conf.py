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

scheduler_group = cfg.OptGroup(name="scheduler",
                               title="Scheduler options")

scheduler_opts = [
    cfg.StrOpt("driver",
               default="filter_scheduler",
               help="""
The class of the driver used by the scheduler. This should be chosen from one
of the entrypoints under the namespace 'trio2o.scheduler.driver' of file
'setup.cfg'. If nothing is specified in this option, the 'filter_scheduler' is
used.

Other options are:
* 'chance_scheduler' which simply picks a pod at random.

Possible values:

* Any of the drivers included in Trio2o:
** filter_scheduler
** chance_scheduler
"""),
]


def register_opts(conf):
    conf.register_group(filter_scheduler_group)
    conf.register_opts(filter_scheduler_opts, group=filter_scheduler_group)

    conf.register_group(scheduler_group)
    conf.register_opts(scheduler_opts, group=scheduler_group)


def unregister_opts(conf):
    conf.unregister_opts(filter_scheduler_opts, group=filter_scheduler_group)
    conf.unregister_opts(scheduler_opts, group=scheduler_group)


def list_opts():
    return [
        ('filter_scheduler', filter_scheduler_opts)
        ('scheduler', scheduler_opts)
    ]
