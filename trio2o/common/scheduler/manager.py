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

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class SchedulerManager(object):
    """Choose a pod run instance on"""

    def __init__(self, scheduler_driver=None):
        if not scheduler_driver:
            scheduler_driver = CONF.scheduler.driver
        self.driver = driver.DriverManager(
            "trio2o.common.scheduler.driver",
            scheduler_driver,
            invoke_on_load=True).driver

    def select_destination(self, context, spec_obj):
        """Returns destinations best suited for this RequestSpec.

        The result should be a single pod.
        """
        dest_pod = self.driver.select_destination(context, spec_obj)
        return dest_pod
