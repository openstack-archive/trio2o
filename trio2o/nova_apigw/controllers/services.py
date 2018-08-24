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

import trio2o.common.client as t_client
import trio2o.common.context as t_context
import trio2o.db.api as db_api


class ServicesController(rest.RestController):

    def __init__(self, project_id):
        self.project_id = project_id

    def _get_client(self, pod_name):
        return t_client.Client(pod_name)

    def _get_all(self, context, params):
        filters = [{'key': key,
                    'comparator': 'eq',
                    'value': value} for key, value in params.iteritems()]
        ret = []
        pods = db_api.list_pods(context)
        for pod in pods:
            if not pod['az_name']:
                continue
            client = self._get_client(pod['pod_name'])
            servers = client.list_services(context, filters=filters)
            ret.extend(servers)
        return ret

    @expose(generic=True, template='json')
    def get_all(self, **kwargs):
        context = t_context.extract_context_from_environ()
        return {'services': self._get_all(context, kwargs)}
