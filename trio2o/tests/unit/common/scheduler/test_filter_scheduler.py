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
from trio2o.common import request_spec
from trio2o.common.scheduler import filter_scheduler
from trio2o.db import api
from trio2o.db import core
from trio2o.tests.unit.common.scheduler import utils

import unittest


class FilterSchedulerTest(unittest.TestCase):

    def setUp(self):
        core.initialize()
        core.ModelBase.metadata.create_all(core.get_engine())
        self.context = context.Context()
        self.project_id = 'test_fs_project'
        self.az_name_1 = 'b_az_fs_1'
        self.az_name_2 = 'b_az_fs_2'

        self.b_pod_1 = {'pod_id': 'b_pod_fs_uuid_1',
                        'pod_name': 'b_region_fs_1',
                        'az_name': self.az_name_1,
                        'is_under_maintenance': False}

        self.b_pod_2 = {'pod_id': 'b_pod_fs_uuid_2',
                        'pod_name': 'b_region_fs_2',
                        'az_name': self.az_name_2,
                        'is_under_maintenance': False}

        self.b_pod_3 = {'pod_id': 'b_pod_fs_uuid_3',
                        'pod_name': 'b_region_fs_3',
                        'az_name': self.az_name_2,
                        'is_under_maintenance': False}

        self.filter_scheduler = filter_scheduler.FilterScheduler()

    def _prepare_binding(self, pod_id):
        binding = {'tenant_id': self.project_id,
                   'pod_id': pod_id,
                   'is_binding': True}
        api.create_pod_binding(self.context, self.project_id, pod_id)
        return binding

    def test_select_destination(self):
        for count, pod in enumerate((self.b_pod_1, self.b_pod_2,
                                     self.b_pod_3)):
            api.create_pod(self.context, pod)
            # disk=4gb*(count+1), ram=1024mb*(count+1), vcpus=4*(count+1)
            utils.create_pod_state_for_pod(self.context, pod['pod_id'],
                                           count+1)
        spec_obj = request_spec.RequestSpec(self.project_id,
                                            disk_gb=8,
                                            memory_mb=1024)

        # b_pod_3 has biggest weight, so the filter scheduler returns b_pod_3
        pod, _ = self.filter_scheduler.select_destination(
            self.context, spec_obj)
        self.assertEqual("b_region_fs_3", pod['pod_name'])
        self.assertEqual("b_pod_fs_uuid_3", pod['pod_id'])

        # request has pod affinity tag, so filter scheduler will returns the
        # pod meet requirements, we create pod affinity tag for b_pod_2, so
        # even b_pod_3 has biggest weight, but filter scheduler will returns
        # b_pod_2.
        key_value_pairs = {"volume": 'SSD'}
        utils.create_pod_affinity_tag(self.context, self.b_pod_2['pod_id'],
                                      **key_value_pairs)

        spec_obj = request_spec.RequestSpec(self.project_id,
                                            disk_gb=8,
                                            memory_mb=2048,
                                            affinity_tags={'volume': "SSD"})
        pod, _ = self.filter_scheduler.select_destination(
            self.context, spec_obj)
        self.assertEqual("b_region_fs_2", pod['pod_name'])
        self.assertEqual("b_pod_fs_uuid_2", pod['pod_id'])

    def tearDown(self):
        core.ModelBase.metadata.drop_all(core.get_engine())
