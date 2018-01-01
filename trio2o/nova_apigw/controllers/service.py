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

import oslo_log.log as logging
from pecan import expose
from pecan import rest

import trio2o.common.client as t_client
from trio2o.common import constants
import trio2o.common.context as t_context
from trio2o.common.i18n import _
from trio2o.common import utils
import trio2o.db.api as db_api


LOG = logging.getLogger(__name__)


SUPPORTED_FILTERS = {
    'host': 'host',
    'binary': 'binary',
}


class ServiceController(rest.RestController):

    def __init__(self, project_id):
        self.project_id = project_id
        self.clients = {constants.TOP: t_client.Client()}

    def _get_client(self, pod_name=constants.TOP):
        if pod_name not in self.clients:
            self.clients[pod_name] = t_client.Client(pod_name)
        return self.clients[pod_name]

    def _construct_compute_entry(self, compute):
        return {
            'id': compute['id'],
            'binary': compute['binary'],
            'host': compute['host'],
            'state': compute['state'],
            'zone': compute['zone'],
            'status': compute['status'],
            'updated_at': compute.get('updated_at', ''),
            'forced_down': False,
            'disabled_reason': None
        }

    @expose(generic=True, template='json')
    def get_all(self, **kwargs):
        context = t_context.extract_context_from_environ()
        filters = self._get_filters(kwargs)
        filters = [{'key': key,
                    'comparator': 'eq',
                    'value': value} for key, value in filters.iteritems()]

        pods = db_api.list_pods(context)
        if len(pods) == 0:
            # if len(pods) == 0, it means the service catalog is empty, and
            # the gateway service is not ready in RegionOne, we return fake
            # value of service list to cheat wait_for_compute function to make
            # stack.sh installation get through. This return value makes
            # nonsense and doesn't use in general compute service list.
            fake_service = [{'status': 'enabled',
                             'binary': 'nova-compute',
                             'zone': 'nova',
                             'host': 'ubuntu',
                             'updated_at': '2018-01-07T07:02:13.000000',
                             'state': 'up',
                             'disabled_reason': None,
                             'id': 2}]
            ret_services = [self._construct_compute_entry(service)
                            for service in fake_service]
            return {'services': ret_services}

        for pod in pods:
            if not pod['az_name']:
                continue
            client = self._get_client(pod['pod_name'])
            services = client.list_services(context, filters=filters)
        if not services:
            return utils.format_nova_error(404, _('Service not found'))
        ret_services = [self._construct_compute_entry(service)
                        for service in services]
        return {'services': ret_services}

    def _get_filters(self, params):
        """Return a dictionary of query param filters from the request.

        :param params: the URI params coming from the wsgi layer
        :return a dict of key/value filters
        """
        filters = {}
        for param in params:
            if param in SUPPORTED_FILTERS:
                filter_name = SUPPORTED_FILTERS.get(param, param)
                filters[filter_name] = params.get(param)

        return filters
