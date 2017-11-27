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

from trio2o.common import context
from trio2o.common.scheduler import weights
from trio2o.common.scheduler.weights import base_weights
from trio2o.common.scheduler.weights import disk
from trio2o.common.scheduler.weights import ram
from trio2o.common.scheduler.weights import vcpu
from trio2o.common.scheduler.weights import workload
from trio2o.db import core
from trio2o.tests.unit.common.scheduler import utils

import unittest


class TestWeigher(unittest.TestCase):
    def setUp(self):
        core.initialize()
        core.ModelBase.metadata.create_all(core.get_engine())
        self.context = context.Context()

    def test_no_multiplier(self):
        class FakeWeigher(base_weights.BaseWeigher):
            def _weigh_object(self, *args, **kwargs):
                pass

        self.assertEqual(1.0,
                         FakeWeigher().weight_multiplier())

    def test_no_weight_object(self):
        class FakeWeigher(base_weights.BaseWeigher):
            def weight_multiplier(self, *args, **kwargs):
                pass
        self.assertRaises(TypeError,
                          FakeWeigher)

    def test_normalization(self):
        # weight_list, expected_result, minval, maxval
        map_ = (
            ((), (), None, None),
            ((0.0, 0.0), (0.0, 0.0), None, None),
            ((1.0, 1.0), (0.0, 0.0), None, None),

            ((20.0, 50.0), (0.0, 1.0), None, None),
            ((20.0, 50.0), (0.0, 0.375), None, 100.0),
            ((20.0, 50.0), (0.4, 1.0), 0.0, None),
            ((20.0, 50.0), (0.2, 0.5), 0.0, 100.0),
        )
        for seq, result, minval, maxval in map_:
            ret = base_weights.normalize(seq, minval=minval, maxval=maxval)
            self.assertEqual(tuple(ret), result)

    def test_only_one_pod(self):
        pod = utils.create_pod(self.context, 'BottomPod_01', 'az_01')
        pod_state = utils.create_pod_state_for_pod(self.context, pod['pod_id'],
                                                   1)
        pod_state_objs = [pod_state]

        weight_handler = weights.PodWeightHandler()
        weighers = [ram.RamWeigher()]
        weighed_pod = weight_handler.get_weighted_objects(weighers,
                                                          pod_state_objs, {})
        self.assertEqual(1, len(weighed_pod))
        self.assertEqual(pod['pod_id'],
                         weighed_pod[0].obj['pod_id'])

    def test_weight_handler(self):
        # Double check at least a couple of known weighers exist
        weight_handler = weights.PodWeightHandler()
        classes = weight_handler.get_matching_classes(
            ['trio2o.common.scheduler.weights.all_weighers'])
        self.assertIn(ram.RamWeigher, classes)
        self.assertIn(disk.DiskWeigher, classes)
        self.assertIn(vcpu.VCPUWeigher, classes)
        self.assertIn(workload.WorkloadWeigher, classes)

    def tearDown(self):
        core.ModelBase.metadata.drop_all(core.get_engine())
