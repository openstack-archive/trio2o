# Copyright 2016 OpenStack Foundation.
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
import urlparse

from pecan import expose
from pecan import request
from pecan import response
from pecan import rest

from oslo_log import log as logging
from oslo_serialization import jsonutils

from trio2o.common import az_ag
from trio2o.common import constants as cons

import trio2o.common.context as t_context

from trio2o.common import httpclient as hclient
from trio2o.common.i18n import _
from trio2o.common.i18n import _LE
from trio2o.common import utils

import trio2o.db.api as db_api
from trio2o.db import models
from trio2o.db import core

LOG = logging.getLogger(__name__)


class SnapshotController(rest.RestController):
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id

    @expose(generic=True, template='json')
    def post(self, **kw):
        context = t_context.extract_context_from_environ()

        if 'snapshot' not in kw:
            return utils.format_cinder_error(
                400,
                _("Missing required element 'snapshot' in request body."))

        volume_id = kw['snapshot']['volume_id']
        volume_mappings = db_api.get_bottom_mappings_by_top_id(
            context,
            volume_id,
            cons.RT_VOLUME)

        if not volume_mappings:
            return utils.format_cinder_error(
                404,
                _('Volume %(volume_id)s could not be found.') %
                {'volume_id': volume_id}
            )

        pod_name = volume_mappings[0][0]['pod_name']
        t_release = cons.R_MITAKA
        b_release = cons.R_MITAKA

        s_ctx = hclient.get_pod_service_ctx(context,
                                            request.url,
                                            pod_name,
                                            s_type=cons.ST_CINDER)

        if s_ctx['b_url'] == '':
            return utils.format_cinder_error(
                404,
                _('Bottom Pod endpoint incorrect'))

        b_headers = hclient.convert_header(t_release,
                                           b_release,
                                           request.headers)

        t_vol = kw['snapshot']
        b_vol_req = hclient.convert_object(t_release,
                                           b_release,
                                           t_vol,
                                           res_type=cons.RT_SNAPSHOT)

        b_body = jsonutils.dumps({'snapshot': b_vol_req})

        resp = hclient.forward_req(context,
                                   'POST',
                                   b_headers,
                                   s_ctx['b_url'],
                                   b_body)
        b_ret_body = jsonutils.loads(resp.content)
        b_status = resp.status_code
        response.status = b_status
        if b_status == 202:
            if b_ret_body.get('snapshot') is not None:
                b_snapshot = b_ret_body['snapshot']
                try:
                    with context.session.begin():
                        core.create_resource(
                            context, models.ResourceRouting,
                            {'top_id': b_snapshot['id'],
                             'bottom_id': b_snapshot['id'],
                             'pod_id': volume_mappings[0][0]['pod_id'],
                             'project_id': self.tenant_id,
                             'resource_type': cons.RT_SNAPSHOT})
                except Exception as e:
                    LOG.exception(_LE('Failed to create snapshot '
                                      'resource routing'
                                      'top_id: %(top_id)s ,'
                                      'bottom_id: %(bottom_id)s ,'
                                      'pod_id: %(pod_id)s ,'
                                      '%(exception)s '),
                                  {'top_id': b_snapshot['id'],
                                   'bottom_id': b_snapshot['id'],
                                   'pod_id': volume_mappings[0][0]['pod_id'],
                                   'exception': e})
                    return utils.format_cinder_error(
                        500,
                        _('Failed to create snapshot resource routing'))
                vol_ret = hclient.convert_object(t_release,
                                                 b_release,
                                                 b_snapshot,
                                                 res_type=cons.RT_SNAPSHOT)
                return {'snapshot': vol_ret}

        return b_ret_body

    @expose(generic=True, template='json')
    def get_one(self, snapshot_id):
        context = t_context.extract_context_from_environ()

        if snapshot_id == 'detail':
            return {'snapshots': self._get_all(context)}

        t_release = cons.R_MITAKA
        b_release = cons.R_MITAKA
        b_headers = hclient.convert_header(t_release,
                                           b_release,
                                           request.headers)
        mappings = db_api.get_bottom_mappings_by_top_id(
            context,
            snapshot_id,
            cons.RT_SNAPSHOT)
        if not mappings:
            return utils.format_cinder_error(
                404, _('snapshot %s could not be found.') % snapshot_id)
        pod = mappings[0][0]
        if not pod:
            return utils.format_cinder_error(
                404, _('snapshot %s could not be found.') % snapshot_id)
        pod_name = pod['pod_name']

        s_ctx = hclient.get_pod_service_ctx(context,
                                            request.url,
                                            pod_name,
                                            s_type=cons.ST_CINDER)
        if not s_ctx:
            return utils.format_cinder_error(
                404, _('snapshot %s could not be found.') % snapshot_id)

        if s_ctx['b_url'] == '':
            return utils.format_cinder_error(
                404,
                _('Bottom Pod endpoint incorrect'))

        resp = hclient.forward_req(context,
                                   'GET',
                                   b_headers,
                                   s_ctx['b_url'],
                                   request.body)

        b_ret_body = jsonutils.loads(resp.content)

        b_status = resp.status_code
        response.status = b_status
        if b_status == 200:
            if b_ret_body.get('snapshot') is not None:
                b_sps_ret = b_ret_body['snapshot']
                ret_vol = hclient.convert_object(b_release,
                                                 t_release,
                                                 b_sps_ret,
                                                 res_type=cons.RT_SNAPSHOT)

                return {'snapshot': ret_vol}

        # resource not find but routing exist, remove the routing
        if b_status == 404:
            filters = [{'key': 'top_id',
                        'comparator': 'eq',
                        'value': snapshot_id},
                       {'key': 'resource_type',
                        'comparator': 'eq',
                        'value': cons.RT_SNAPSHOT}]
            with context.session.begin():
                core.delete_resources(
                    context,
                    models.ResourceRouting,
                    filters)

        return b_ret_body

    @expose(generic=True, template='json')
    def get_all(self):

        # Lists all Block Storage snapshots, with details,
        #  that the tenant can access.
        context = t_context.extract_context_from_environ()
        return {'snapshots': self._get_all(context)}

    @expose(generic=True, template='json')
    def _get_all(self, context):

        ret = []
        pods = az_ag.list_pods_by_tenant(context,
                                         self.tenant_id)
        for pod in pods:
            if pod['pod_name'] == '':
                continue

            query = urlparse.urlsplit(request.url).query
            query_filters = urlparse.parse_qsl(query)
            skip_pod = False
            for k, v in query_filters:
                if k == 'availability_zone' and v != pod['az_name']:
                    skip_pod = True
                    break
            if skip_pod:
                continue

            s_ctx = hclient.get_pod_service_ctx(
                context,
                request.url,
                pod['pod_name'],
                s_type=cons.ST_CINDER)

            if s_ctx['b_url'] == '':
                LOG.error(
                    _LE("bottom pod endpoint incorrect %s")
                    % pod['pod_name'])
                continue

            # get the release of top and bottom
            t_release = cons.R_MITAKA
            b_release = cons.R_MITAKA

            b_headers = hclient.convert_header(t_release,
                                               b_release,
                                               request.headers)

            resp = hclient.forward_req(context, 'GET',
                                       b_headers,
                                       s_ctx['b_url'],
                                       request.body)
            if resp.status_code == 200:

                routings = db_api.get_bottom_mappings_by_tenant_pod(
                    context, self.tenant_id,
                    pod['pod_id'], cons.RT_SNAPSHOT
                )

                b_ret_body = jsonutils.loads(resp.content)
                if b_ret_body.get('snapshots'):
                    for sna in b_ret_body['snapshots']:

                        if not routings.get(sna['id']):
                            b_ret_body['snapshots'].remove(sna)
                            continue

                        sna['availability_zone'] = pod['az_name']
                    ret.extend(b_ret_body['snapshots'])
        return ret

    @expose(generic=True, template='json')
    def put(self, snapshot_id, **kw):
        # Updates a snapshot
        context = t_context.extract_context_from_environ()

        t_release = cons.R_MITAKA
        b_release = cons.R_MITAKA

        mappings = db_api.get_bottom_mappings_by_top_id(
            context,
            snapshot_id,
            cons.RT_SNAPSHOT)
        if not mappings:
            return utils.format_cinder_error(
                404,
                _('snapshot %s could not be found.') % snapshot_id)

        pod = mappings[0][0]
        if not pod:
            return utils.format_cinder_error(
                404, _('snapshot %s could not be found.') % snapshot_id)
        pod_name = pod['pod_name']

        s_ctx = hclient.get_pod_service_ctx(
            context,
            request.url,
            pod_name,
            s_type=cons.ST_CINDER)

        if not s_ctx:
            return utils.format_cinder_error(
                404,
                _('snapshot %s could not be found.') %
                snapshot_id)

        if s_ctx['b_url'] == '':
            return utils.format_cinder_error(
                404,
                _('Bottom Pod endpoint incorrect'))

        b_headers = hclient.convert_header(t_release,
                                           b_release,
                                           request.headers)

        t_vol = kw['snapshot']

        b_vol_req = hclient.convert_object(t_release,
                                           b_release,
                                           t_vol,
                                           res_type=cons.RT_SNAPSHOT)

        b_body = jsonutils.dumps({'snapshot': b_vol_req})
        resp = hclient.forward_req(context, 'PUT',
                                   b_headers,
                                   s_ctx['b_url'],
                                   b_body)

        b_status = resp.status_code
        b_ret_body = jsonutils.loads(resp.content)
        response.status = b_status

        if b_status == 200:
            if b_ret_body.get('snapshot') is not None:
                b_vol_ret = b_ret_body['snapshot']
                ret_vol = hclient.convert_object(b_release,
                                                 t_release,
                                                 b_vol_ret,
                                                 res_type=cons.RT_SNAPSHOT)

                return {'snapshot': ret_vol}

        # resource not found but routing exist, remove the routing
        if b_status == 404:
            filters = [{'key': 'top_id',
                        'comparator': 'eq',
                        'value': snapshot_id},
                       {'key': 'resource_type',
                        'comparator': 'eq',
                        'value': cons.RT_SNAPSHOT}]
            with context.session.begin():
                core.delete_resources(context,
                                      models.ResourceRouting,
                                      filters)
        return b_ret_body

    @expose(generic=True, template='json')
    def delete(self, snapshot_id):
        context = t_context.extract_context_from_environ()

        t_release = cons.R_MITAKA
        b_release = cons.R_MITAKA

        mappings = db_api.get_bottom_mappings_by_top_id(
            context,
            snapshot_id,
            cons.RT_SNAPSHOT)

        if not mappings:
            return utils.format_cinder_error(
                404, _('snapshot %s could not be found.') % snapshot_id)
        pod = mappings[0][0]
        if not pod:
            return utils.format_cinder_error(
                404, _('snapshot %s could not be found.') % snapshot_id)
        pod_name = pod['pod_name']

        s_ctx = hclient.get_pod_service_ctx(context,
                                            request.url,
                                            pod_name,
                                            s_type=cons.ST_CINDER)
        if not s_ctx:
            return utils.format_cinder_error(
                404, _('snapshot %s could not be found.') % snapshot_id)

        if s_ctx['b_url'] == '':
            return utils.format_cinder_error(
                404, _('Bottom Pod endpoint incorrect'))

        b_headers = hclient.convert_header(t_release,
                                           b_release,
                                           request.headers)
        resp = hclient.forward_req(context,
                                   'DELETE',
                                   b_headers,
                                   s_ctx['b_url'],
                                   request.body)

        response.status = resp.status_code

        return response
