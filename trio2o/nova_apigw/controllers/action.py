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

import pecan
from pecan import expose
from pecan import rest

from oslo_log import log as logging

import trio2o.common.client as t_client
from trio2o.common import constants
import trio2o.common.context as t_context
from trio2o.common.i18n import _
from trio2o.common import utils
import trio2o.db.api as db_api

LOG = logging.getLogger(__name__)


class ActionController(rest.RestController):

    def __init__(self, project_id, server_id):
        self.project_id = project_id
        self.server_id = server_id
        self.clients = {constants.TOP: t_client.Client()}
        self.handle_map = {
            'os-start': self._handle_action,
            'os-stop': self._handle_action,
            'forceDelete': self._handle_action,
            'lock': self._handle_action,
            'unlock': self._handle_action,
            'pause': self._handle_action,
            'unpause': self._handle_action,
            'resume': self._handle_action,
            'suspend': self._handle_action,
            'shelve': self._handle_action,
            'unshelve': self._handle_action,
            'shelveOffload': self._handle_action,
            'migrate': self._handle_action,
            'trigger_crash_dump': self._handle_action,
            'reboot': self._handle_action,
            'resize': self._handle_action,
            'confirmResize': self._handle_action,
            'revertResize': self._handle_action,
            'os-resetState': self._handle_action
        }

    def _get_client(self, pod_name=constants.TOP):
        if pod_name not in self.clients:
            self.clients[pod_name] = t_client.Client(pod_name)
        return self.clients[pod_name]

    def _handle_action(self, context, pod_name, body):
        """Perform a server action

        :param pod_name: the bottom pod name.

        :param body: action parameters body.
        """
        url = constants.SERVER_ACTION_URL % self.server_id
        api = self._get_client(pod_name).get_native_client(constants.RT_SERVER,
                                                           context)
        return api.client.post(url, body=body)

    @expose(generic=True, template='json')
    def post(self, **kw):
        context = t_context.extract_context_from_environ()

        action_handle = None
        action_type = None
        for _type in self.handle_map:
            if _type in kw:
                action_handle = self.handle_map[_type]
                action_type = _type
        if not action_handle:
            return utils.format_nova_error(
                400, _('Server action not supported'))

        server_mappings = db_api.get_bottom_mappings_by_top_id(
            context, self.server_id, constants.RT_SERVER)
        if not server_mappings:
            return utils.format_nova_error(
                404, _('Server %s could not be found') % self.server_id)

        pod_name = server_mappings[0][0]['pod_name']
        try:
            resp, body = action_handle(context, pod_name, kw)
            pecan.response.status = resp.status_code
            if not body:
                return pecan.response
            else:
                return body
        except Exception as e:
            code = 500
            message = _('Action %(action)s on server %(server_id)s fails') % {
                'action': action_type,
                'server_id': self.server_id}
            if hasattr(e, 'code'):
                code = e.code
            ex_message = str(e)
            if ex_message:
                message = ex_message
            LOG.error(message)
            return utils.format_nova_error(code, message)
