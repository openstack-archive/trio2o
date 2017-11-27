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
from trio2o.common.scheduler.filters import availability_zone_filter
from trio2o.db import core
from trio2o.tests.unit.common.scheduler import utils

import unittest


class TestAvailabilityZoneFilter(unittest.TestCase):

    def setUp(self):
        core.initialize()
        core.ModelBase.metadata.create_all(core.get_engine())
        self.context = context.Context()
        self.filt_cls = availability_zone_filter.AvailabilityZoneFilter()

    def test_availability_zone_filter_fails(self):
        # az_name is empty
        project_id = uuidutils.generate_uuid()
        spec_obj = request_spec.RequestSpec(project_id, az_name='')

        pod = utils.create_pod(self.context, 'BottomPod_01', 'az_01')
        utils.create_pod_state_for_pod(self.context, pod['pod_id'], 1)
        self.assertFalse(self.filt_cls.is_pod_passed(self.context, pod,
                                                     spec_obj))

        # az_name doesn't match
        project_id = uuidutils.generate_uuid()
        spec_obj = request_spec.RequestSpec(project_id).to_dict()
        spec_obj.update({'az_name': "fake_az_name"})

        pod = utils.create_pod(self.context, 'BottomPod_02', 'az_02')
        utils.create_pod_state_for_pod(self.context, pod['pod_id'], 1)
        self.assertFalse(self.filt_cls.is_pod_passed(self.context, pod,
                                                     spec_obj))

    def test_availability_zone_filter_passes(self):
        # az_name is not empty
        project_id = uuidutils.generate_uuid()
        spec_obj = request_spec.RequestSpec(project_id, az_name='az_02')

        pod = utils.create_pod(self.context, 'BottomPod_03', 'az_02')
        utils.create_pod_state_for_pod(self.context, pod['pod_id'], 1)
        self.assertTrue(self.filt_cls.is_pod_passed(self.context, pod,
                                                    spec_obj))

        # az_name is None
        project_id = uuidutils.generate_uuid()
        spec_obj = request_spec.RequestSpec(project_id)

        pod = utils.create_pod(self.context, 'BottomPod_04', 'az_03')
        utils.create_pod_state_for_pod(self.context, pod['pod_id'], 1)
        self.assertTrue(self.filt_cls.is_pod_passed(self.context, pod,
                                                    spec_obj))

        def tearDown(self):
            core.ModelBase.metadata.drop_all(core.get_engine())
