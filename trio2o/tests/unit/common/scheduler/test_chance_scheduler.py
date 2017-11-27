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
from trio2o.common.scheduler import chance_scheduler
from trio2o.db import api
from trio2o.db import core
from trio2o.tests.unit.common.scheduler import utils

import unittest


class ChanceSchedulerTest(unittest.TestCase):

    def setUp(self):
        core.initialize()
        core.ModelBase.metadata.create_all(core.get_engine())
        self.context = context.Context()
        self.project_id = 'fake_project_id'
        self.az_name_1 = 'az1'
        self.az_name_2 = 'az2'

        self.b_pod_1 = {'pod_id': 'fake_pod_id_1',
                        'pod_name': 'Pod1',
                        'az_name': self.az_name_1,
                        'is_under_maintenance': True}

        self.b_pod_2 = {'pod_id': 'fake_pod_id_2',
                        'pod_name': 'RegionOne',
                        'az_name': '',
                        'is_under_maintenance': False}

        self.b_pod_3 = {'pod_id': 'fake_pod_id_3',
                        'pod_name': 'Pod2',
                        'az_name': self.az_name_2,
                        'is_under_maintenance': False}

        self.b_pod_4 = {'pod_id': 'fake_pod_id_4',
                        'pod_name': 'Pod3',
                        'az_name': self.az_name_1,
                        'is_under_maintenance': False}

        self.chance_scheduler = chance_scheduler.ChanceScheduler()

    def test_select_destination(self):
        for count, pod in enumerate((self.b_pod_1, self.b_pod_2,
                                     self.b_pod_3)):
            api.create_pod(self.context, pod)

        spec_obj = request_spec.RequestSpec(self.project_id,
                                            disk_gb=8,
                                            memory_mb=1024)

        # There are only three pods in db: Pod1 is under maintenance, RegionOne
        # is top pod, therefore the chance scheduler will choose Pod2
        pod = self.chance_scheduler.select_destination(self.context, spec_obj)
        self.assertEqual("Pod2", pod['pod_name'])
        self.assertEqual("fake_pod_id_3", pod['pod_id'])

        # request has pod affinity tag, so chance scheduler will returns the
        # pod meet requirements, we create pod affinity tag for Pod3, so
        # Pod3 will be chosen.
        api.create_pod(self.context, self.b_pod_4)
        key_value_pairs = {"volume": 'SSD'}
        utils.create_pod_affinity_tag(self.context, self.b_pod_4['pod_id'],
                                      **key_value_pairs)

        spec_obj = request_spec.RequestSpec(self.project_id,
                                            disk_gb=8,
                                            memory_mb=2048,
                                            affinity_tags={'volume': "SSD"})
        pod = self.chance_scheduler.select_destination(self.context, spec_obj)
        self.assertEqual("Pod3", pod['pod_name'])
        self.assertEqual("fake_pod_id_4", pod['pod_id'])

    def tearDown(self):
        core.ModelBase.metadata.drop_all(core.get_engine())
