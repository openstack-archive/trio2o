# Copyright (c) 2015 Huawei Tech. Co., Ltd.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from mock import patch
import pecan
import unittest

from oslo_serialization import jsonutils
from oslo_utils import uuidutils

from trio2o.cinder_apigw.controllers import volume_backup as backup
from trio2o.common import constants
from trio2o.common import context
from trio2o.common import httpclient as hclient
from trio2o.db import api
from trio2o.db import core
from trio2o.db import models


class FakeResponse(object):
    def __new__(cls, code=500):
        cls.status = code
        cls.status_code = code
        cls.content = None
        return super(FakeResponse, cls).__new__(cls)


class FakeRequest(object):
    def __new__(cls, *args, **kwargs):
        cls.url = '/lodfdfdf'
        cls.header = None
        return super(FakeRequest, cls).__new__(cls)


class VolumeBackupsTest(unittest.TestCase):
    def setUp(self):
        core.initialize()
        core.ModelBase.metadata.create_all(core.get_engine())
        self.context = context.Context()
        self.project_id = 'test_project'
        self.context.tenant = self.project_id
        self.controller = backup.VolumeBackupController(self.project_id)

    def _prepare_pod(self, bottom_pod_num=1):
        t_pod = {'pod_id': 't_pod_uuid', 'pod_name': 't_region',
                 'az_name': ''}
        api.create_pod(self.context, t_pod)
        b_pods = []
        if bottom_pod_num == 1:
            b_pod = {'pod_id': 'b_pod_uuid', 'pod_name': 'b_region',
                     'az_name': 'b_az'}
            api.create_pod(self.context, b_pod)
            b_pods.append(b_pod)
        else:
            for i in xrange(1, bottom_pod_num + 1):
                b_pod = {'pod_id': 'b_pod_%d_uuid' % i,
                         'pod_name': 'b_region_%d' % i,
                         'az_name': 'b_az_%d' % i}
                api.create_pod(self.context, b_pod)
                b_pods.append(b_pod)
        return t_pod, b_pods

    def _prepare_volume(self, pod):
        t_volume_id = uuidutils.generate_uuid()
        b_volume_id = t_volume_id
        with self.context.session.begin():
            core.create_resource(
                self.context, models.ResourceRouting,
                {'top_id': t_volume_id, 'bottom_id': b_volume_id,
                 'pod_id': pod['pod_id'], 'project_id': self.project_id,
                 'resource_type': constants.RT_VOLUME})
        return t_volume_id

    def _prepare_pod_service(self, pod_id, service):
        config_dict = {'service_id': uuidutils.generate_uuid(),
                       'pod_id': pod_id,
                       'service_type': service,
                       'service_url': 'fake_pod_service'}
        api.create_pod_service_configuration(self.context, config_dict)
        pass

    def _prepare_server(self, pod):
        t_server_id = uuidutils.generate_uuid()
        b_server_id = t_server_id
        with self.context.session.begin():
            core.create_resource(
                self.context, models.ResourceRouting,
                {'top_id': t_server_id, 'bottom_id': b_server_id,
                 'pod_id': pod['pod_id'], 'project_id': self.project_id,
                 'resource_type': constants.RT_SERVER})
        return t_server_id

    @patch.object(pecan, 'response', new=FakeResponse)
    @patch.object(jsonutils, 'loads')
    @patch.object(hclient, 'forward_req')
    @patch.object(pecan, 'request')
    @patch.object(context, 'extract_context_from_environ')
    def test_create_backup(self, mock_context, mock_request,
                           mock_forward_req, mock_loads):
        mock_context.return_value = self.context
        pecan.core.state = mock_request
        mock_forward_req.return_value = FakeResponse(200)
        fake_resp = {'fakeresp': 'fakeresp'}
        mock_loads.return_value = fake_resp
        t_pod, b_pods = self._prepare_pod()
        self._prepare_pod_service(b_pods[0]['pod_id'], constants.ST_CINDER)
        t_volume_id = self._prepare_volume(b_pods[0])

        body = {"backup": {"container": None,
                           "description": None,
                           "name": "backup001",
                           "volume_id": t_volume_id,
                           "incremental": True}}

        res = self.controller.post(**body)
        self.assertEqual(fake_resp, res)

    def tearDown(self):
        core.ModelBase.metadata.drop_all(core.get_engine())
