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

from trio2o.common.scheduler import driver as trio2o_driver
from trio2o.db import api as db_api

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class SchedulerManager(trio2o_driver.Scheduler):
    """Choose a pod run instance on"""

    def __init__(self, scheduler_driver=None, *args, **kwargs):
        if not scheduler_driver:
            scheduler_driver = CONF.scheduler.driver
        self.driver = driver.DriverManager(
            "trio2o.common.scheduler.driver",
            scheduler_driver,
            invoke_on_load=True).driver
        super(SchedulerManager, self).__init__(*args, **kwargs)

    def select_destination(self, context, spec_obj):
        """Returns destinations best suited for this RequestSpec.

        The result should be a single pod.
        """
        dest_pod = self.driver.select_destination(context, spec_obj)
        return dest_pod

    def create_podbinding(self, context, project_id, pod):
        # If the tenant current binds with a pod, then we update
        # the binding relationship, otherwise we create new binding
        filter_binding = [{'key': 'tenant_id', 'comparator': 'eq',
                           'value': project_id},
                          {'key': 'pod_id', 'comparator': 'eq',
                           'value': pod['pod_id']}
                          ]
        binding = db_api.get_pod_binding_by_tenant_id(context,
                                                      filter_binding)

        if binding:
            self.pod_manager.update_binding(context, project_id, pod)
        else:
            self.pod_manager.create_binding(context, project_id, pod)
