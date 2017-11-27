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

from oslo_utils import uuidutils

from trio2o.common import context
from trio2o.common import request_spec
from trio2o.common.scheduler.filters import pod_affinity_tag_filter
from trio2o.db import core
from trio2o.tests.unit.common.scheduler import utils

import unittest


class TestPodAffinityTagFilter(unittest.TestCase):

    def setUp(self):
        core.initialize()
        core.ModelBase.metadata.create_all(core.get_engine())
        self.context = context.Context()
        self.filt_cls = pod_affinity_tag_filter.PodAffinityTagFilter()

    def test_ignore_pod_filter_fails(self):
        project_id = uuidutils.generate_uuid()
        spec_obj = request_spec.RequestSpec(project_id,
                                            affinity_tags={'volume': "SSD"})
        pod = utils.create_pod(self.context, 'bottom_pod_0001', 'az_0001')
        utils.create_pod_state_for_pod(self.context, pod['pod_id'], 1)
        key_value_pairs = {"type": 'CONTAINER'}
        utils.create_pod_affinity_tag(self.context, pod['pod_id'],
                                      **key_value_pairs)
        self.assertFalse(self.filt_cls.is_pod_passed(self.context, pod,
                                                     spec_obj))

    def test_ignore_pod_filter_passes(self):
        project_id = uuidutils.generate_uuid()
        spec_obj = request_spec.RequestSpec(project_id,
                                            affinity_tags={'volume': "SSD"})

        pod = utils.create_pod(self.context, 'bottom_pod_0011', 'az_0002')
        utils.create_pod_state_for_pod(self.context, pod['pod_id'], 2)
        key_value_pairs = {"volume": 'SSD'}
        utils.create_pod_affinity_tag(self.context, pod['pod_id'],
                                      **key_value_pairs)
        self.assertTrue(self.filt_cls.is_pod_passed(self.context, pod,
                                                    spec_obj))

        project_id = uuidutils.generate_uuid()
        spec_obj = request_spec.RequestSpec(
            project_id, affinity_tags={'type': 'CONTAINER'})

        pod = utils.create_pod(self.context, 'bottom_pod_0012', 'az_0003')
        utils.create_pod_state_for_pod(self.context, pod['pod_id'], 1)
        key_value_pairs = {"type": 'CONTAINER', 'volume': "SSD"}
        utils.create_pod_affinity_tag(self.context, pod['pod_id'],
                                      **key_value_pairs)
        self.assertTrue(self.filt_cls.is_pod_passed(self.context, pod,
                                                    spec_obj))

    def tearDown(self):
        core.ModelBase.metadata.drop_all(core.get_engine())
