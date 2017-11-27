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

from trio2o.common.scheduler import weights

CONF = cfg.CONF


class WorkloadWeigher(weights.BasePodWeigher):
    def weight_multiplier(self):
        """Override the weight multiplier"""
        return CONF.workload_weight_multiplier

    def _weigh_object(self, pod_state, weight_properties):
        """Higher weights win.  We want spreading to be the default."""
        # we use 'running vms' to denote the workload in a pod, because
        # 'current workload' in pod state is not accurate enough.
        return pod_state['running_vms']
