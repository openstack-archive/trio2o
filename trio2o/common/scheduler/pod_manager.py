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
from stevedore import driver

from trio2o.common import exceptions
from trio2o.common.i18n import _LE
from trio2o.common.i18n import _LI
from trio2o.common.scheduler import filters
from trio2o.common.scheduler.filters import tenant_filter
from trio2o.common.scheduler import weights
from trio2o.db import api as db_api

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class PodManager(object):
    def __init__(self):
        self.filter_handler = filters.PodFilterHandler()
        filter_classes = self.filter_handler.get_matching_classes(
            CONF.filter_scheduler.available_filters)
        self.filter_cls_map = {cls.__name__: cls for cls in filter_classes}
        self.filter_obj_map = {}
        self.enabled_filters = self._choose_pod_filters(self._load_filters())
        self.weight_handler = weights.PodWeightHandler()
        weigher_classes = self.weight_handler.get_matching_classes(
            CONF.filter_scheduler.weight_classes)
        self.weighers = [cls() for cls in weigher_classes]

    def enable_tenant_filter(self):
        tenant_filter_enabled = False
        for filter_ in self.enabled_filters:
            if isinstance(filter_, tenant_filter.TenantFilter):
                tenant_filter_enabled = True
                break
        if not tenant_filter_enabled:
            self.enabled_filters.append(tenant_filter.TenantFilter())

    def disable_tenant_filter(self):
        for filter_ in self.enabled_filters:
            if isinstance(filter_, tenant_filter.TenantFilter):
                self.enabled_filters.remove(filter_)
                break

    def _choose_pod_filters(self, filter_cls_names):
        """Since the caller may specify which filters to use we need

        to have an authoritative list of what is permissible. This
        function checks the filter names against a predefined set
        of acceptable filters.
        """
        if not isinstance(filter_cls_names, (list, tuple)):
            filter_cls_names = [filter_cls_names]

        good_filters = []
        bad_filters = []
        for filter_name in filter_cls_names:
            if filter_name not in self.filter_obj_map:
                if filter_name not in self.filter_cls_map:
                    bad_filters.append(filter_name)
                    continue
                filter_cls = self.filter_cls_map[filter_name]
                self.filter_obj_map[filter_name] = filter_cls()
            good_filters.append(self.filter_obj_map[filter_name])
        if bad_filters:
            msg = ", ".join(bad_filters)
            raise exceptions.SchedulerPodFilterNotFound(filter_name=msg)
        return good_filters

    def _load_filters(self):
        # default enabled filters, these are basic filters to use
        enabled_filter_cls_names = CONF.filter_scheduler.enabled_filters

        # apart from the default enabled filters, we can use extra filters
        # configured in setup.cfg
        for filter_name in self.filter_cls_map.keys():
            if filter_name in enabled_filter_cls_names:
                continue
            try:
                driver.DriverManager(
                    namespace='trio2o.common.scheduler.extra_filters',
                    name=filter_name,
                    invoke_on_load=False
                )
                enabled_filter_cls_names.append(filter_name)
            except Exception:
                pass
        return enabled_filter_cls_names

    @staticmethod
    def get_current_bound_pods(context, tenant_id):
        binding_filter = [{'key': 'tenant_id', 'comparator': 'eq',
                           'value': tenant_id}]
        pods = []
        bindings = db_api.get_pod_binding_by_tenant_id(context, binding_filter)
        for binding in bindings:
            pods.append(db_api.get_pod_by_pod_id(context, binding['pod_id']))
        return pods

    @staticmethod
    def create_binding(context, tenant_id, pod_id):
        try:
            db_api.create_pod_binding(context, tenant_id, pod_id)
        except Exception as e:
            LOG.error(_LE('Fail to create pod binding: %(exception)s'),
                      {'exception': e})
            return False
        return True

    @staticmethod
    def update_binding(context, project_id, pod):
        # If there exist a pod that had been bound with tenant in the same az,
        # then update its binding state to False.
        filter_binding = [{'key': 'tenant_id', 'comparator': 'eq',
                           'value': project_id},
                          {'key': 'is_binding', 'comparator': 'eq',
                           'value': True},
                          ]
        bindings = db_api.list_podbindings(context, filter_binding)
        if len(bindings) == 0:
            db_api.create_pod_binding(context, project_id, pod['pod_id'])
            return True
        for binding in bindings:
            pod_b = db_api.get_pod_by_pod_id(context, binding['pod_id'])
            if (pod_b['az_name'] == pod['az_name'] and
                    pod_b['pod_id'] != pod['pod_id']):
                binding['is_binding'] = False
                try:
                    db_api.change_pod_binding(
                        context, binding, pod['pod_id'])
                except Exception as e:
                    LOG.error(_LE('Fail to update pod binding: %(exception)s'),
                              {'exception': e})
                    return False
        return True

    @staticmethod
    def get_all_pod_states(context, pod_list):
        pod_state_objs = []
        for pod in pod_list:
            pod_state_obj = db_api.get_pod_state_by_pod_id(context,
                                                           pod['pod_id'])
            if pod_state_obj is not None:
                pod_state_objs.append(pod_state_obj)
        return pod_state_objs

    def get_filtered_pods(self, context, pods, spec_obj):
        if not isinstance(spec_obj, dict):
            spec_obj = spec_obj.to_dict()

        def _get_pods_matching_request(pods, requested_destination):
            target_pods = []
            for pod in pods:
                if pod['pod_name'] == requested_destination:
                    target_pods.append(pod)
                    break
            if target_pods:
                LOG.info(_LI('Pod filter only checking destination pod name'
                             ' %(name)s '), {'name': requested_destination})
            else:
                # The API level should prevent the user from providing a wrong
                # destination but let's make sure a wrong destination doesn't
                # trample the scheduler still.
                LOG.info(_LI('No pods matched due to not matching requested '
                             'destination (%(pod_name)s'),
                         {'pod_name': requested_destination})
            return iter(target_pods)

        ignored_pods = spec_obj['ignore_pods']
        requested_pod_name = spec_obj['requested_destination']

        def strip_ignore_pods(pods, pods_to_ignore):
            pods_ret = []
            for pod_name in pods_to_ignore:
                for pod in pods:
                    if pod_name == pod['pod_name']:
                        continue
                    else:
                        pods_ret.append(pod)
            return pods_ret

        if requested_pod_name is not None:
            # Reduce a potentially long set of pods as much as possible to any
            # requested destination pods before passing the list to the filters
            pods = _get_pods_matching_request(pods, requested_pod_name)

        if ignored_pods:
            pods = strip_ignore_pods(pods, ignored_pods)

        return self.filter_handler.get_filtered_objects(context,
                                                        self.enabled_filters,
                                                        pods,
                                                        spec_obj)

    def get_weighed_pods(self, pod_states, weighing_properties):
        """Weigh the pods."""
        return self.weight_handler.get_weighted_objects(self.weighers,
                                                        pod_states,
                                                        weighing_properties)

    def get_all_enabled_filters(self):
        return self.enabled_filters
