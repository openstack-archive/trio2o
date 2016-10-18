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
import six

import oslo_log.log as logging

from trio2o.common import az_ag
import trio2o.common.client as t_client
from trio2o.common import constants
import trio2o.common.context as t_context
import trio2o.common.exceptions as t_exceptions
from trio2o.common.i18n import _
from trio2o.common.i18n import _LE
import trio2o.common.lock_handle as t_lock
from trio2o.common.quota import QUOTAS
from trio2o.common import utils
from trio2o.common import xrpcapi
import trio2o.db.api as db_api
from trio2o.db import core
from trio2o.db import models

LOG = logging.getLogger(__name__)

MAX_METADATA_KEY_LENGTH = 255
MAX_METADATA_VALUE_LENGTH = 255


class ServerController(rest.RestController):

    def __init__(self, project_id):
        self.project_id = project_id
        self.clients = {constants.TOP: t_client.Client()}
        self.xjob_handler = xrpcapi.XJobAPI()

    def _get_client(self, pod_name=constants.TOP):
        if pod_name not in self.clients:
            self.clients[pod_name] = t_client.Client(pod_name)
        return self.clients[pod_name]

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
            servers = client.list_servers(context, filters=filters)
            ret.extend(servers)
        return ret

    @staticmethod
    def _construct_brief_server_entry(server):
        return {'id': server['id'],
                'name': server.get('name'),
                'links': server.get('links')}

    @expose(generic=True, template='json')
    def get_one(self, _id, **kwargs):
        context = t_context.extract_context_from_environ()

        if _id == 'detail':
            # return {'servers': [self._construct_brief_server_entry(
            #     server) for server in self._get_all(context, kwargs)]}
            return {'servers': self._get_all(context, kwargs)}

        mappings = db_api.get_bottom_mappings_by_top_id(
            context, _id, constants.RT_SERVER)
        if not mappings:
            return utils.format_nova_error(
                404, _('Instance %s could not be found.') % _id)
        pod, bottom_id = mappings[0]
        client = self._get_client(pod['pod_name'])
        server = client.get_servers(context, bottom_id)
        if not server:
            return utils.format_nova_error(
                404, _('Instance %s could not be found.') % _id)
        else:
            return {'server': server}

    @expose(generic=True, template='json')
    def get_all(self, **kwargs):
        context = t_context.extract_context_from_environ()
        # return {'servers': [self._construct_brief_server_entry(
        #     server) for server in self._get_all(context, kwargs)]}
        return {'servers': self._get_all(context, kwargs)}

    @expose(generic=True, template='json')
    def post(self, **kw):
        context = t_context.extract_context_from_environ()

        if 'server' not in kw:
            return utils.format_nova_error(
                400, _('server is not set'))

        az = kw['server'].get('availability_zone', '')

        pod, b_az = az_ag.get_pod_by_az_tenant(
            context, az, self.project_id)
        if not pod:
            return utils.format_nova_error(
                500, _('Pod not configured or scheduling failure'))

        t_server_dict = kw['server']
        self._process_metadata_quota(context, t_server_dict)
        self._process_injected_file_quota(context, t_server_dict)

        server_body = self._get_create_server_body(kw['server'], b_az)

        security_groups = []
        if 'security_groups' not in kw['server']:
            security_groups = ['default']
        else:
            for sg in kw['server']['security_groups']:
                if 'name' not in sg:
                    return utils.format_nova_error(
                        400, _('Invalid input for field/attribute'))
                security_groups.append(sg['name'])

        server_body['networks'] = []
        if 'networks' in kw['server']:
            for net_info in kw['server']['networks']:
                if 'uuid' in net_info:
                    nic = {'net-id': net_info['uuid']}
                    server_body['networks'].append(nic)
                elif 'port' in net_info:
                    nic = {'port-id': net_info['port']}
                    server_body['networks'].append(nic)

        client = self._get_client(pod['pod_name'])
        server = client.create_servers(
            context,
            name=server_body['name'],
            image=server_body['imageRef'],
            flavor=server_body['flavorRef'],
            nics=server_body['networks'],
            security_groups=security_groups)

        with context.session.begin():
            core.create_resource(context, models.ResourceRouting,
                                 {'top_id': server['id'],
                                  'bottom_id': server['id'],
                                  'pod_id': pod['pod_id'],
                                  'project_id': self.project_id,
                                  'resource_type': constants.RT_SERVER})
        pecan.response.status = 202
        return {'server': server}

    @expose(generic=True, template='json')
    def delete(self, _id):
        context = t_context.extract_context_from_environ()

        mappings = db_api.get_bottom_mappings_by_top_id(context, _id,
                                                        constants.RT_SERVER)
        if not mappings:
            pecan.response.status = 404
            return {'Error': {'message': _('Server not found'), 'code': 404}}

        pod, bottom_id = mappings[0]
        client = self._get_client(pod['pod_name'])
        try:
            ret = client.delete_servers(context, bottom_id)
            # none return value indicates server not found
            if ret is None:
                self._remove_stale_mapping(context, _id)
                pecan.response.status = 404
                return {'Error': {'message': _('Server not found'),
                                  'code': 404}}
        except Exception as e:
            code = 500
            message = _('Delete server %(server_id)s fails') % {
                'server_id': _id}
            if hasattr(e, 'code'):
                code = e.code
            ex_message = str(e)
            if ex_message:
                message = ex_message
            LOG.error(message)

            pecan.response.status = code
            return {'Error': {'message': message, 'code': code}}

        pecan.response.status = 204
        return pecan.response

    def _get_or_create_route(self, context, pod, _id, _type):
        def list_resources(t_ctx, q_ctx, pod_, ele, _type_):
            client = self._get_client(pod_['pod_name'])
            return client.list_resources(_type_, t_ctx, [{'key': 'name',
                                                          'comparator': 'eq',
                                                          'value': ele['id']}])

        return t_lock.get_or_create_route(context, None,
                                          self.project_id, pod, {'id': _id},
                                          _type, list_resources)

    @staticmethod
    def _get_create_server_body(origin, bottom_az):
        body = {}
        copy_fields = ['name', 'imageRef', 'flavorRef',
                       'max_count', 'min_count']
        if bottom_az:
            body['availability_zone'] = bottom_az
        for field in copy_fields:
            if field in origin:
                body[field] = origin[field]
        return body

    @staticmethod
    def _remove_stale_mapping(context, server_id):
        filters = [{'key': 'top_id', 'comparator': 'eq', 'value': server_id},
                   {'key': 'resource_type',
                    'comparator': 'eq',
                    'value': constants.RT_SERVER}]
        with context.session.begin():
            core.delete_resources(context,
                                  models.ResourceRouting,
                                  filters)

    def _process_injected_file_quota(self, context, t_server_dict):
        try:
            ctx = context.elevated()
            injected_files = t_server_dict.get('injected_files', None)
            self._check_injected_file_quota(ctx, injected_files)
        except (t_exceptions.OnsetFileLimitExceeded,
                t_exceptions.OnsetFilePathLimitExceeded,
                t_exceptions.OnsetFileContentLimitExceeded) as e:
            msg = str(e)
            LOG.exception(_LE('Quota exceeded %(msg)s'),
                          {'msg': msg})
            return utils.format_nova_error(400, _('Quota exceeded %s') % msg)

    def _check_injected_file_quota(self, context, injected_files):
        """Enforce quota limits on injected files.

        Raises a QuotaError if any limit is exceeded.

        """

        if injected_files is None:
            return

        # Check number of files first
        try:
            QUOTAS.limit_check(context,
                               injected_files=len(injected_files))
        except t_exceptions.OverQuota:
            raise t_exceptions.OnsetFileLimitExceeded()

        # OK, now count path and content lengths; we're looking for
        # the max...
        max_path = 0
        max_content = 0
        for path, content in injected_files:
            max_path = max(max_path, len(path))
            max_content = max(max_content, len(content))

        try:
            QUOTAS.limit_check(context,
                               injected_file_path_bytes=max_path,
                               injected_file_content_bytes=max_content)
        except t_exceptions.OverQuota as exc:
            # Favor path limit over content limit for reporting
            # purposes
            if 'injected_file_path_bytes' in exc.kwargs['overs']:
                raise t_exceptions.OnsetFilePathLimitExceeded()
            else:
                raise t_exceptions.OnsetFileContentLimitExceeded()

    def _process_metadata_quota(self, context, t_server_dict):
        try:
            ctx = context.elevated()
            metadata = t_server_dict.get('metadata', None)
            self._check_metadata_properties_quota(ctx, metadata)
        except t_exceptions.InvalidMetadata as e1:
            LOG.exception(_LE('Invalid metadata %(exception)s'),
                          {'exception': str(e1)})
            return utils.format_nova_error(400, _('Invalid metadata'))
        except t_exceptions.InvalidMetadataSize as e2:
            LOG.exception(_LE('Invalid metadata size %(exception)s'),
                          {'exception': str(e2)})
            return utils.format_nova_error(400, _('Invalid metadata size'))
        except t_exceptions.MetadataLimitExceeded as e3:
            LOG.exception(_LE('Quota exceeded %(exception)s'),
                          {'exception': str(e3)})
            return utils.format_nova_error(400,
                                           _('Quota exceeded in metadata'))

    def _check_metadata_properties_quota(self, context, metadata=None):
        """Enforce quota limits on metadata properties."""
        if not metadata:
            metadata = {}
        if not isinstance(metadata, dict):
            msg = (_("Metadata type should be dict."))
            raise t_exceptions.InvalidMetadata(reason=msg)
        num_metadata = len(metadata)
        try:
            QUOTAS.limit_check(context, metadata_items=num_metadata)
        except t_exceptions.OverQuota as exc:
            quota_metadata = exc.kwargs['quotas']['metadata_items']
            raise t_exceptions.MetadataLimitExceeded(allowed=quota_metadata)

        # Because metadata is processed in the bottom pod, we just do
        # parameter validation here to ensure quota management
        for k, v in six.iteritems(metadata):
            try:
                utils.check_string_length(v)
                utils.check_string_length(k, min_len=1)
            except t_exceptions.InvalidInput as e:
                raise t_exceptions.InvalidMetadata(reason=str(e))

            if len(k) > MAX_METADATA_KEY_LENGTH:
                msg = _("Metadata property key greater than 255 characters")
                raise t_exceptions.InvalidMetadataSize(reason=msg)
            if len(v) > MAX_METADATA_VALUE_LENGTH:
                msg = _("Metadata property value greater than 255 characters")
                raise t_exceptions.InvalidMetadataSize(reason=msg)
