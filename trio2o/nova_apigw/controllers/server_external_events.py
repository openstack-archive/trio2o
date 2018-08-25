# Copyright (c) 2018 ZTCloud. Co., Ltd.
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

from pecan import expose
from pecan import rest

import oslo_log.log as logging
import trio2o.common.client as t_client
import trio2o.common.context as t_context
import trio2o.db.api as db_api
from trio2o.common import constants
from trio2o.common.i18n import _
from trio2o.common import utils

LOG = logging.getLogger(__name__)


class ServerExternalEventController(rest.RestController):

    def __init__(self, project_id):
        self.project_id = project_id

    def _get_client(self, pod_name):
        return t_client.Client(pod_name)

    @expose(generic=True, template='json')
    def post(self, **kwargs):
        context = t_context.extract_context_from_environ()
        events = kwargs['events']
        LOG.debug('%s', kwargs)
        server_uuid = events[0]['server_uuid']
        mappings = db_api.get_bottom_mappings_by_top_id(
            context, server_uuid, constants.RT_SERVER)
        if not mappings:
            return utils.format_nova_error(
                404, _('Instance %s could not be found.') % server_uuid)

        pod = mappings[0][0]
        client = self._get_client(pod['pod_name'])
        return client.create_server_external_events(context, events)
