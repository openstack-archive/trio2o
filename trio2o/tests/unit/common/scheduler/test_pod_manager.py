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
from stevedore import driver

from trio2o.common import context
from trio2o.common import request_spec
from trio2o.common.scheduler.filters import tenant_filter
from trio2o.db import api
from trio2o.db import core
from trio2o.db import models
from trio2o.tests.unit.common.scheduler import utils

import unittest


class PodManagerTest(unittest.TestCase):
    def setUp(self):
        core.initialize()
        core.ModelBase.metadata.create_all(core.get_engine())
        self.context = context.Context()
        self.project_id = 'test_pm_project'
        self.az_name_2 = 'b_az_pm_2'
        self.az_name_1 = 'b_az_pm_1'
        self.pod_manager = driver.DriverManager(
            namespace='trio2o.common.schedulers',
            name='pod_manager',
            invoke_on_load=True
        ).driver
        self.b_pod_1 = {'pod_id': 'b_pod_pm_uuid_1',
                        'pod_name': 'b_region_pm_1',
                        'az_name': self.az_name_1,
                        'is_under_maintenance': False}

        self.b_pod_2 = {'pod_id': 'b_pod_pm_uuid_2',
                        'pod_name': 'b_region_pm_2',
                        'az_name': self.az_name_2,
                        'is_under_maintenance': False}

        self.b_pod_3 = {'pod_id': 'b_pod_pm_uuid_3',
                        'pod_name': 'b_region_pm_3',
                        'az_name': self.az_name_2,
                        'is_under_maintenance': False}

        self.b_pod_4 = {'pod_id': 'b_pod_pm_uuid_4',
                        'pod_name': 'b_region_pm_4',
                        'az_name': self.az_name_2,
                        'is_under_maintenance': False}
        self.b_pod_5 = {'pod_id': 'b_pod_pm_uuid_5',
                        'pod_name': 'b_region_pm_5',
                        'az_name': "az_name_5",
                        'is_under_maintenance': True}

    def test_get_current_bound_pods(self):
        api.create_pod(self.context, self.b_pod_1)
        api.create_pod_binding(
            self.context, self.project_id, self.b_pod_1['pod_id'])

        pods_1 = self.pod_manager.get_current_bound_pods(
            self.context, self.project_id)
        bindings_1 = core.query_resource(
            self.context, models.PodBinding,
            [{'key': 'tenant_id',
              'comparator': 'eq',
              'value': self.project_id}], [])
        self.assertEqual(len(pods_1), 1)
        self.assertEqual(len(bindings_1), 1)
        self.assertEqual(self.b_pod_1['pod_id'], pods_1[0]['pod_id'])

        pods_2 = self.pod_manager.get_current_bound_pods(
            self.context, 'new_project_pm_1')
        bindings_2 = core.query_resource(
            self.context, models.PodBinding,
            [{'key': 'tenant_id',
              'comparator': 'eq',
              'value': 'new_project_pm_1'}], [])
        self.assertEqual(len(bindings_2), 0)
        self.assertEqual(pods_2, [])

    def test_create_binding(self):
        api.create_pod(self.context, self.b_pod_2)
        flag = self.pod_manager.create_binding(
            self.context, 'new_project_pm_2', self.b_pod_2['pod_id'])
        self.assertEqual(flag, True)
        binding_q = core.query_resource(
            self.context, models.PodBinding,
            [{'key': 'tenant_id',
              'comparator': 'eq',
              'value': 'new_project_pm_2'}], [])
        self.assertEqual(len(binding_q), 1)
        self.assertEqual(binding_q[0]['pod_id'], self.b_pod_2['pod_id'])
        self.assertEqual(binding_q[0]['tenant_id'], 'new_project_pm_2')
        self.assertEqual(binding_q[0]['is_binding'], True)

    def test_update_binding(self):
        api.create_pod(self.context, self.b_pod_4)
        api.create_pod(self.context, self.b_pod_3)
        flag = self.pod_manager.create_binding(
            self.context, 'new_project_pm_3', self.b_pod_3['pod_id'])
        self.assertEqual(flag, True)
        current_binding = core.query_resource(
            self.context, models.PodBinding,
            [{'key': 'tenant_id',
              'comparator': 'eq',
              'value': 'new_project_pm_3'}], [])

        flag = self.pod_manager.update_binding(
            self.context, current_binding[0]['tenant_id'],
            self.b_pod_4)
        self.assertEqual(flag, True)
        binding_q = core.query_resource(
            self.context, models.PodBinding,
            [{'key': 'tenant_id',
              'comparator': 'eq',
              'value': 'new_project_pm_3'}], [])
        self.assertEqual(len(binding_q), 2)
        self.assertEqual(binding_q[0]['pod_id'], self.b_pod_3['pod_id'])
        self.assertEqual(binding_q[0]['tenant_id'], 'new_project_pm_3')
        self.assertEqual(binding_q[0]['is_binding'], False)
        self.assertEqual(binding_q[1]['pod_id'], self.b_pod_4['pod_id'])
        self.assertEqual(binding_q[1]['tenant_id'], 'new_project_pm_3')
        self.assertEqual(binding_q[1]['is_binding'], True)

    def test_enable_tenant_filter(self):
        self.pod_manager.disable_tenant_filter()
        self.pod_manager.enable_tenant_filter()
        enabled_filters = self.pod_manager.get_all_enabled_filters()
        is_tenant_filter_enabled = False
        for filter_ in enabled_filters:
            if isinstance(filter_, tenant_filter.TenantFilter):
                is_tenant_filter_enabled = True
        self.assertTrue(is_tenant_filter_enabled)

    def test_disable_tenant_filter(self):
        self.pod_manager.enable_tenant_filter()
        self.pod_manager.disable_tenant_filter()
        enabled_filters = self.pod_manager.get_all_enabled_filters()
        is_tenant_filter_disabled = True
        for filter_ in enabled_filters:
            if isinstance(filter_, tenant_filter.TenantFilter):
                is_tenant_filter_disabled = False
        self.assertTrue(is_tenant_filter_disabled)

    def test_get_all_pod_states(self):
        api.create_pod(self.context, self.b_pod_3)
        utils.create_pod_state_for_pod(self.context, self.b_pod_3['pod_id'])

        api.create_pod(self.context, self.b_pod_4)
        utils.create_pod_state_for_pod(self.context, self.b_pod_4['pod_id'])

        pod_list = api.list_pods(self.context)
        pod_state_objs = self.pod_manager.get_all_pod_states(self.context,
                                                             pod_list)
        self.assertEqual(len(pod_list), len(pod_state_objs))

    def test_get_filtered_unbound_pods(self):
        self.pod_manager.disable_tenant_filter()

        for count, pod in enumerate((self.b_pod_1, self.b_pod_2, self.b_pod_3,
                                    self.b_pod_5)):
            api.create_pod(self.context, pod)
            # disk=4gb*(count+1), ram=1024mb*(count+1), vcpus=4*(count+1)
            utils.create_pod_state_for_pod(self.context, pod['pod_id'],
                                           count+1)

        # test case 1: disk=4, ram=1024, all pods apart from b_pod_5 can't
        # get through
        project_id = uuidutils.generate_uuid()
        spec_obj = request_spec.RequestSpec(project_id,
                                            disk_gb=4,
                                            memory_mb=1024)
        pod_list = api.list_pods(self.context)

        pods = self.pod_manager.get_filtered_pods(self.context, pod_list,
                                                  spec_obj)
        self.assertEqual(3, len(pods))

        # test case 2: disk=8, ram=2048, only b_pod_2 and b_pod_3 can
        # get through
        project_id = uuidutils.generate_uuid()
        spec_obj = request_spec.RequestSpec(project_id,
                                            disk_gb=8,
                                            memory_mb=2048)
        pod_list = api.list_pods(self.context)

        pods = self.pod_manager.get_filtered_pods(self.context, pod_list,
                                                  spec_obj)
        self.assertEqual(2, len(pods))

        # test case 3: disk=8, ram=2048, pod_affinity_tag=SSD, only b_pod_3 can
        # get through
        # create pod affinity tag for b_pod_3, the pod_affinity_tag filter is
        # enabled in default filters.
        key_value_pairs = {"volume": 'SSD'}
        utils.create_pod_affinity_tag(self.context, self.b_pod_3['pod_id'],
                                      **key_value_pairs)

        spec_obj = request_spec.RequestSpec(project_id,
                                            disk_gb=8,
                                            memory_mb=2048,
                                            affinity_tags={'volume': "SSD"})

        pod_list = api.list_pods(self.context)
        self.pod_manager.disable_tenant_filter()
        pods = self.pod_manager.get_filtered_pods(self.context, pod_list,
                                                  spec_obj)
        self.assertEqual(1, len(pods))

    def test_get_filtered_bound_pods(self):
        self.pod_manager.enable_tenant_filter()

        for count, pod in enumerate((self.b_pod_1, self.b_pod_2, self.b_pod_3,
                                     self.b_pod_5)):
            api.create_pod(self.context, pod)
            # disk=4gb*(count+1), ram=1024mb*(count+1), vcpus=4*(count+1)
            utils.create_pod_state_for_pod(self.context, pod['pod_id'],
                                           count+1)

        # create pod binding
        api.create_pod_binding(self.context, self.project_id,
                               self.b_pod_3['pod_id'])
        # test case 1: disk=4, ram=1024, only b_pod_3 can get through
        spec_obj = request_spec.RequestSpec(self.project_id,
                                            disk_gb=8,
                                            memory_mb=1024)
        pod_list = api.list_pods(self.context)

        pods = self.pod_manager.get_filtered_pods(self.context, pod_list,
                                                  spec_obj)
        self.assertEqual(1, len(pods))

        # test case 2: disk=8, ram=2048, only b_pod_2 and b_pod_3 are bound
        # with tenant, but request has pod affinity tag
        api.create_pod_binding(self.context, self.project_id,
                               self.b_pod_2['pod_id'])
        key_value_pairs = {"volume": 'SSD'}
        utils.create_pod_affinity_tag(self.context, self.b_pod_2['pod_id'],
                                      **key_value_pairs)

        spec_obj = request_spec.RequestSpec(self.project_id,
                                            disk_gb=8,
                                            memory_mb=2048,
                                            affinity_tags={'volume': "SSD"})
        pod_list = api.list_pods(self.context)

        pods = self.pod_manager.get_filtered_pods(self.context, pod_list,
                                                  spec_obj)
        self.assertEqual(1, len(pods))

    def test_get_weighed_pods(self):
        for count, pod in enumerate((self.b_pod_1, self.b_pod_2, self.b_pod_3,
                                     self.b_pod_5)):
            api.create_pod(self.context, pod)
            # disk=4gb*(count+1), ram=1024mb*(count+1), vcpus=4*(count+1)
            utils.create_pod_state_for_pod(self.context, pod['pod_id'],
                                           count+1)
        pod_state_objs = api.list_pod_states(self.context)
        weighed_pods = self.pod_manager.get_weighed_pods(pod_state_objs, {})
        self.assertEqual(1.0, weighed_pods[0].weight)
        self.assertEqual(0.0, weighed_pods[-1].weight)

    def tearDown(self):
        core.ModelBase.metadata.drop_all(core.get_engine())
