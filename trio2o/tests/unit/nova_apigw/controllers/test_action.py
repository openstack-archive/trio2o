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

from oslo_utils import uuidutils

from trio2o.common import client
from trio2o.common import constants
from trio2o.common import context
from trio2o.common import exceptions
from trio2o.db import api
from trio2o.db import core
from trio2o.db import models
from trio2o.nova_apigw.controllers import action


class FakeResponse(object):
    def __new__(cls, code=500):
        cls.status = code
        cls.status_code = code
        return super(FakeResponse, cls).__new__(cls)


class ActionTest(unittest.TestCase):
    def setUp(self):
        core.initialize()
        core.ModelBase.metadata.create_all(core.get_engine())
        self.context = context.get_admin_context()
        self.project_id = 'test_project'
        self.controller = action.ActionController(self.project_id, '')

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

    def _validate_error_code(self, res, code):
        self.assertEqual(code, res[res.keys()[0]]['code'])

    @patch.object(pecan, 'response', new=FakeResponse)
    @patch.object(context, 'extract_context_from_environ')
    def test_action_not_supported(self, mock_context):
        mock_context.return_value = self.context

        body = {'unsupported_action': ''}
        res = self.controller.post(**body)
        self._validate_error_code(res, 400)

    @patch.object(pecan, 'response', new=FakeResponse)
    @patch.object(context, 'extract_context_from_environ')
    def test_action_server_not_found(self, mock_context):
        mock_context.return_value = self.context

        body = {'os-start': ''}
        res = self.controller.post(**body)
        self._validate_error_code(res, 404)

    @patch.object(pecan, 'response', new=FakeResponse)
    @patch.object(client.Client, 'action_resources')
    @patch.object(context, 'extract_context_from_environ')
    def test_action_exception(self, mock_context, mock_action):
        mock_context.return_value = self.context

        t_pod, b_pods = self._prepare_pod()
        t_server_id = self._prepare_server(b_pods[0])
        self.controller.server_id = t_server_id

        mock_action.side_effect = exceptions.HTTPForbiddenError(
            msg='Server operation forbidden')
        body = {'os-start': ''}
        res = self.controller.post(**body)
        self._validate_error_code(res, 403)

        mock_action.side_effect = exceptions.ServiceUnavailable
        body = {'os-start': ''}
        res = self.controller.post(**body)
        self._validate_error_code(res, 500)

        mock_action.side_effect = Exception
        body = {'os-start': ''}
        res = self.controller.post(**body)
        self._validate_error_code(res, 500)

    @patch.object(pecan, 'response', new=FakeResponse)
    @patch.object(client.Client, 'action_resources')
    @patch.object(context, 'extract_context_from_environ')
    def test_start_action(self, mock_context, mock_action):
        mock_context.return_value = self.context
        mock_action.return_value = (FakeResponse(202), None)

        t_pod, b_pods = self._prepare_pod()
        t_server_id = self._prepare_server(b_pods[0])
        self.controller.server_id = t_server_id

        body = {'os-start': ''}
        res = self.controller.post(**body)
        mock_action.assert_called_once_with(
            'server', self.context, 'start', t_server_id)
        self.assertEqual(202, res.status)

    @patch.object(pecan, 'response', new=FakeResponse)
    @patch.object(client.Client, 'action_resources')
    @patch.object(context, 'extract_context_from_environ')
    def test_stop_action(self, mock_context, mock_action):
        mock_context.return_value = self.context
        mock_action.return_value = (FakeResponse(202), None)

        t_pod, b_pods = self._prepare_pod()
        t_server_id = self._prepare_server(b_pods[0])
        self.controller.server_id = t_server_id

        body = {'os-stop': ''}
        res = self.controller.post(**body)
        mock_action.assert_called_once_with(
            'server', self.context, 'stop', t_server_id)
        self.assertEqual(202, res.status)

    @patch.object(pecan, 'response', new=FakeResponse)
    @patch.object(client.Client, 'action_resources')
    @patch.object(context, 'extract_context_from_environ')
    def test_force_delete_action(self, mock_context, mock_action):
        mock_context.return_value = self.context
        mock_action.return_value = (FakeResponse(202), None)

        t_pod, b_pods = self._prepare_pod()
        t_server_id = self._prepare_server(b_pods[0])
        self.controller.server_id = t_server_id

        body = {'forceDelete': ''}
        res = self.controller.post(**body)
        mock_action.assert_called_once_with(
            'server', self.context, 'force_delete', t_server_id)
        self.assertEqual(202, res.status)

    @patch.object(pecan, 'response', new=FakeResponse)
    @patch.object(client.Client, 'action_resources')
    @patch.object(context, 'extract_context_from_environ')
    def test_lock_action(self, mock_context, mock_action):
        mock_context.return_value = self.context
        mock_action.return_value = (FakeResponse(202), None)

        t_pod, b_pods = self._prepare_pod()
        t_server_id = self._prepare_server(b_pods[0])
        self.controller.server_id = t_server_id

        body = {'lock': ''}
        res = self.controller.post(**body)
        mock_action.assert_called_once_with(
            'server', self.context, 'lock', t_server_id)
        self.assertEqual(202, res.status)

    @patch.object(pecan, 'response', new=FakeResponse)
    @patch.object(client.Client, 'action_resources')
    @patch.object(context, 'extract_context_from_environ')
    def test_unlock_action(self, mock_context, mock_action):
        mock_context.return_value = self.context
        mock_action.return_value = (FakeResponse(202), None)

        t_pod, b_pods = self._prepare_pod()
        t_server_id = self._prepare_server(b_pods[0])
        self.controller.server_id = t_server_id

        body = {'unlock': ''}
        res = self.controller.post(**body)
        mock_action.assert_called_once_with(
            'server', self.context, 'unlock', t_server_id)
        self.assertEqual(202, res.status)

    @patch.object(pecan, 'response', new=FakeResponse)
    @patch.object(client.Client, 'action_resources')
    @patch.object(context, 'extract_context_from_environ')
    def test_pause_action(self, mock_context, mock_action):
        mock_context.return_value = self.context
        mock_action.return_value = (FakeResponse(202), None)

        t_pod, b_pods = self._prepare_pod()
        t_server_id = self._prepare_server(b_pods[0])
        self.controller.server_id = t_server_id

        body = {'pause': ''}
        res = self.controller.post(**body)
        mock_action.assert_called_once_with(
            'server', self.context, 'pause', t_server_id)
        self.assertEqual(202, res.status)

    @patch.object(pecan, 'response', new=FakeResponse)
    @patch.object(client.Client, 'action_resources')
    @patch.object(context, 'extract_context_from_environ')
    def test_unpause_action(self, mock_context, mock_action):
        mock_context.return_value = self.context
        mock_action.return_value = (FakeResponse(202), None)

        t_pod, b_pods = self._prepare_pod()
        t_server_id = self._prepare_server(b_pods[0])
        self.controller.server_id = t_server_id

        body = {'unpause': ''}
        res = self.controller.post(**body)
        mock_action.assert_called_once_with(
            'server', self.context, 'unpause', t_server_id)
        self.assertEqual(202, res.status)

    @patch.object(pecan, 'response', new=FakeResponse)
    @patch.object(client.Client, 'action_resources')
    @patch.object(context, 'extract_context_from_environ')
    def test_suspend_action(self, mock_context, mock_action):
        mock_context.return_value = self.context
        mock_action.return_value = (FakeResponse(202), None)

        t_pod, b_pods = self._prepare_pod()
        t_server_id = self._prepare_server(b_pods[0])
        self.controller.server_id = t_server_id

        body = {'suspend': ''}
        res = self.controller.post(**body)
        mock_action.assert_called_once_with(
            'server', self.context, 'suspend', t_server_id)
        self.assertEqual(202, res.status)

    @patch.object(pecan, 'response', new=FakeResponse)
    @patch.object(client.Client, 'action_resources')
    @patch.object(context, 'extract_context_from_environ')
    def test_resume_action(self, mock_context, mock_action):
        mock_context.return_value = self.context
        mock_action.return_value = (FakeResponse(202), None)

        t_pod, b_pods = self._prepare_pod()
        t_server_id = self._prepare_server(b_pods[0])
        self.controller.server_id = t_server_id

        body = {'resume': ''}
        res = self.controller.post(**body)
        mock_action.assert_called_once_with(
            'server', self.context, 'resume', t_server_id)
        self.assertEqual(202, res.status)

    @patch.object(pecan, 'response', new=FakeResponse)
    @patch.object(client.Client, 'action_resources')
    @patch.object(context, 'extract_context_from_environ')
    def test_shelveOffload_action(self, mock_context, mock_action):
        mock_context.return_value = self.context
        mock_action.return_value = (FakeResponse(202), None)

        t_pod, b_pods = self._prepare_pod()
        t_server_id = self._prepare_server(b_pods[0])
        self.controller.server_id = t_server_id

        body = {'shelveOffload': ''}
        res = self.controller.post(**body)
        mock_action.assert_called_once_with(
            'server', self.context, 'shelve_offload', t_server_id)
        self.assertEqual(202, res.status)

    @patch.object(pecan, 'response', new=FakeResponse)
    @patch.object(client.Client, 'action_resources')
    @patch.object(context, 'extract_context_from_environ')
    def test_shelve_action(self, mock_context, mock_action):
        mock_context.return_value = self.context
        mock_action.return_value = (FakeResponse(202), None)

        t_pod, b_pods = self._prepare_pod()
        t_server_id = self._prepare_server(b_pods[0])
        self.controller.server_id = t_server_id

        body = {'shelve': ''}
        res = self.controller.post(**body)
        mock_action.assert_called_once_with(
            'server', self.context, 'shelve', t_server_id)
        self.assertEqual(202, res.status)

    @patch.object(pecan, 'response', new=FakeResponse)
    @patch.object(client.Client, 'action_resources')
    @patch.object(context, 'extract_context_from_environ')
    def test_unshelve_action(self, mock_context, mock_action):
        mock_context.return_value = self.context
        mock_action.return_value = (FakeResponse(202), None)

        t_pod, b_pods = self._prepare_pod()
        t_server_id = self._prepare_server(b_pods[0])
        self.controller.server_id = t_server_id

        body = {'unshelve': ''}
        res = self.controller.post(**body)
        mock_action.assert_called_once_with(
            'server', self.context, 'unshelve', t_server_id)
        self.assertEqual(202, res.status)

    @patch.object(pecan, 'response', new=FakeResponse)
    @patch.object(client.Client, 'action_resources')
    @patch.object(context, 'extract_context_from_environ')
    def test_trigger_crash_dump_action(self, mock_context, mock_action):
        mock_context.return_value = self.context
        mock_action.return_value = (FakeResponse(202), None)

        t_pod, b_pods = self._prepare_pod()
        t_server_id = self._prepare_server(b_pods[0])
        self.controller.server_id = t_server_id

        body = {'trigger_crash_dump': ''}
        res = self.controller.post(**body)
        mock_action.assert_called_once_with(
            'server', self.context, 'trigger_crash_dump', t_server_id)
        self.assertEqual(202, res.status)

    @patch.object(pecan, 'response', new=FakeResponse)
    @patch.object(client.Client, 'action_resources')
    @patch.object(context, 'extract_context_from_environ')
    def test_migrate_action(self, mock_context, mock_action):
        mock_context.return_value = self.context
        mock_action.return_value = (FakeResponse(202), None)

        t_pod, b_pods = self._prepare_pod()
        t_server_id = self._prepare_server(b_pods[0])
        self.controller.server_id = t_server_id

        body = {'migrate': ''}
        res = self.controller.post(**body)
        mock_action.assert_called_once_with(
            'server', self.context, 'migrate', t_server_id)
        self.assertEqual(202, res.status)

    def tearDown(self):
        core.ModelBase.metadata.drop_all(core.get_engine())
