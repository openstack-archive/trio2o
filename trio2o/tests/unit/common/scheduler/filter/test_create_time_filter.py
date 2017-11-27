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

from datetime import datetime
from oslo_utils import uuidutils

from trio2o.common import context
from trio2o.common import request_spec
from trio2o.common.scheduler.filters import create_time_filter
from trio2o.db import core
from trio2o.tests.unit.common.scheduler import utils

import unittest


class TestCreateTimeFilter(unittest.TestCase):

    def setUp(self):
        core.initialize()
        core.ModelBase.metadata.create_all(core.get_engine())
        self.context = context.Context()
        self.filt_cls = create_time_filter.CreateTimeFilter()

    def test_create_time_filter_fails(self):
        project_id = uuidutils.generate_uuid()
        spec_obj = request_spec.RequestSpec(project_id,
                                            create_time=datetime(2017, 12, 14))
        pod = utils.create_pod(self.context,
                               'BottomPod_013', 'az_013',
                               datetime(2016, 12, 13))
        utils.create_pod_state_for_pod(self.context, pod['pod_id'], 1)
        self.assertFalse(self.filt_cls.is_pod_passed(self.context, pod,
                                                     spec_obj))

    def test_create_time_filter_passes(self):
        project_id = uuidutils.generate_uuid()
        spec_obj = request_spec.RequestSpec(
            project_id, create_time=datetime(2017, 12, 14))

        pod = utils.create_pod(self.context, 'BottomPod_014', 'az_013',
                               datetime(2017, 12, 15))
        utils.create_pod_state_for_pod(self.context, pod['pod_id'], 1)
        self.assertTrue(self.filt_cls.is_pod_passed(self.context, pod,
                                                    spec_obj))

        project_id = uuidutils.generate_uuid()
        spec_obj = request_spec.RequestSpec(
            project_id, datetime(2017, 12, 15)).to_dict()
        spec_obj.update({'create_time': None})

        pod = utils.create_pod(self.context, 'BottomPod_015', 'az_014',
                               datetime(2017, 12, 15))
        utils.create_pod_state_for_pod(self.context, pod['pod_id'], 1)
        self.assertTrue(self.filt_cls.is_pod_passed(self.context, pod,
                                                    spec_obj))

    def tearDown(self):
        core.ModelBase.metadata.drop_all(core.get_engine())
