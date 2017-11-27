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
import unittest

from trio2o.common import context
from trio2o.common.scheduler import scheduler_conf
from trio2o.common.scheduler import weights
from trio2o.common.scheduler.weights import vcpu
from trio2o.db import api as db_api
from trio2o.db import core
from trio2o.tests.unit.common.scheduler import utils


class TestVCPUWeigher(unittest.TestCase):
    def setUp(self):
        cfg.CONF.clear()
        cfg.CONF.register_opts(scheduler_conf.filter_scheduler_opts)

        core.initialize()
        core.ModelBase.metadata.create_all(core.get_engine())
        self.context = context.Context()
        self.weight_handler = weights.PodWeightHandler()
        self.weighers = [vcpu.VCPUWeigher()]

    def _get_weighed_pod(self, pod_state_objs, weight_properties=None):
        if weight_properties is None:
            weight_properties = {}
        return self.weight_handler.get_weighted_objects(self.weighers,
                                                        pod_state_objs,
                                                        weight_properties)[0]

    def _get_all_pod_state_objects(self, count=2):
        pod_state_objs = []
        for i in xrange(1, count + 1):
            pod_name = 'bottom_pod_0' + str(i)
            az_name = 'az_name_0' + str(i)
            pod = utils.create_pod(self.context, pod_name, az_name)
            pod_state = utils.create_pod_state_for_pod(self.context,
                                                       pod['pod_id'],
                                                       i)
            pod_state_objs.append(pod_state)
        return pod_state_objs

    def test_default_of_spreading_first(self):
        pos_object_list = self._get_all_pod_state_objects(3)

        # pod1: free_vcpus=4*1
        # pod2: free_vcpus=4*2
        # pod3: free_vcpus=4*3

        # so, pod3 should win:
        weighed_pod = self._get_weighed_pod(pos_object_list)
        self.assertEqual(1.0, weighed_pod.weight)
        pod = db_api.get_pod_by_pod_id(self.context, weighed_pod.obj['pod_id'])
        self.assertEqual('bottom_pod_03', pod['pod_name'])

    def test_vcpu_filter_multiplier1(self):
        vcpu_weight_multiplier_backup = cfg.CONF.vcpu_weight_multiplier
        cfg.CONF.set_override('vcpu_weight_multiplier', 0.0,
                              scheduler_conf.filter_scheduler_group)

        pod_object_list = self._get_all_pod_state_objects(3)
        # pod1: free_vcpus=4*1
        # pod2: free_vcpus=4*2
        # pod3: free_vcpus=4*3

        # # We do not know the pod, all have same weight.
        weighed_pod = self._get_weighed_pod(pod_object_list)
        self.assertEqual(0.0, weighed_pod.weight)

        cfg.CONF.set_override('vcpu_weight_multiplier',
                              vcpu_weight_multiplier_backup,
                              scheduler_conf.filter_scheduler_group)

    def test_vcpu_filter_multiplier2(self):
        vcpu_weight_multiplier_backup = cfg.CONF.vcpu_weight_multiplier
        cfg.CONF.set_override('vcpu_weight_multiplier', 2.0,
                              scheduler_conf.filter_scheduler_group)

        pod_object_list = self._get_all_pod_state_objects(3)
        # pod1: free_vcpus=4*1
        # pod2: free_vcpus=4*2
        # pod3: free_vcpus=4*3

        # so, pod3 should win:
        weighed_pod = self._get_weighed_pod(pod_object_list)
        self.assertEqual(1.0 * 2, weighed_pod.weight)

        pod = db_api.get_pod_by_pod_id(self.context, weighed_pod.obj['pod_id'])
        self.assertEqual('bottom_pod_03', pod['pod_name'])

        cfg.CONF.set_override('vcpu_weight_multiplier',
                              vcpu_weight_multiplier_backup,
                              scheduler_conf.filter_scheduler_group)

    def test_vcpu_filter_negative(self):
        vcpu_weight_multiplier_backup = cfg.CONF.vcpu_weight_multiplier
        cfg.CONF.set_override('vcpu_weight_multiplier', -1.0,
                              scheduler_conf.filter_scheduler_group)

        pod_object_list = self._get_all_pod_state_objects(3)
        # pod1: free_vcpus=4*1
        # pod2: free_vcpus=4*2
        # pod3: free_vcpus=4*3

        # so, pod1 should win:
        weighed_pod = self._get_weighed_pod(pod_object_list)
        self.assertEqual(0.0, weighed_pod.weight)

        pod = db_api.get_pod_by_pod_id(self.context, weighed_pod.obj['pod_id'])
        self.assertEqual('bottom_pod_01', pod['pod_name'])

        cfg.CONF.set_override('vcpu_weight_multiplier',
                              vcpu_weight_multiplier_backup,
                              scheduler_conf.filter_scheduler_group)

    def tearDown(self):
        cfg.CONF.unregister_opts(scheduler_conf.filter_scheduler_opts)
        core.ModelBase.metadata.drop_all(core.get_engine())
