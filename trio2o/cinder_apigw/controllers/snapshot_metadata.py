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


from pecan import expose
from pecan import request
from pecan import response
from pecan import rest

from oslo_log import log as logging
from oslo_serialization import jsonutils

from trio2o.common import constants as cons
import trio2o.common.context as t_context
from trio2o.common import httpclient as hclient
from trio2o.common.i18n import _
from trio2o.common.i18n import _LE
from trio2o.common import utils
import trio2o.db.api as db_api

LOG = logging.getLogger(__name__)


class SnapshotMetaDataController(rest.RestController):
    def __init__(self, tenant_id, snapshot_id):
        self.tenant_id = tenant_id
        self.snapshot_id = snapshot_id

    @expose(generic=True, template='json')
    def post(self, **kw):
        """Create snapshot metadata associated with a snapshot.

            :param kw: dictionary of values to be created
            :returns: created snapshot metadata
        """
        context = t_context.extract_context_from_environ()
        if 'metadata' not in kw:
            return utils.format_cinder_error(
                400, _("Missing required element 'metadata' in "
                       "request body."))

        try:
            mappings = db_api.get_bottom_mappings_by_top_id(
                context,
                self.snapshot_id,
                cons.RT_SNAPSHOT)
            if not mappings:
                return utils.format_cinder_error(
                    404,
                    _('snapshot %s could not be found.') % self.snapshot_id)
            pod = mappings[0][0]
            if not pod:
                return utils.format_cinder_error(
                    404,
                    _('snapshot %s could not be found.') % self.snapshot_id)

            t_pod = db_api.get_top_pod(context)
            if not t_pod:
                LOG.error(_LE("Top Pod not configured"))
                return utils.format_cinder_error(
                    500, _('Top Pod not configured'))
        except Exception as e:
            LOG.exception(
                _LE('Fail to create metadata for a snapshot:'
                    '%(snapshot_id)s'
                    '%(exception)s'),
                {'snapshot_id': self.snapshot_id,
                 'exception': e})
            return utils.format_cinder_error(
                500,
                _('Fail to create metadata'))

        t_release = cons.R_MITAKA
        b_release = cons.R_MITAKA

        s_ctx = hclient.get_pod_service_ctx(
            context,
            request.url,
            pod['pod_name'],
            s_type=cons.ST_CINDER)

        if s_ctx['b_url'] == '':
            LOG.error(
                _LE("Bottom pod endpoint incorrect %s") %
                pod['pod_name'])
            return utils.format_cinder_error(
                500,
                _('Bottom pod endpoint incorrect'))

        b_headers = hclient.convert_header(t_release,
                                           b_release,
                                           request.headers)

        t_metadata = kw['metadata']

        # add or remove key-value in the request for diff. version
        b_sps_req = hclient.convert_object(t_release,
                                           b_release,
                                           t_metadata,
                                           res_type=cons.RT_VOl_METADATA)

        b_body = jsonutils.dumps({'metadata': b_sps_req})

        resp = hclient.forward_req(
            context,
            'POST',
            b_headers,
            s_ctx['b_url'],
            b_body)
        b_status = resp.status_code
        b_body_ret = jsonutils.loads(resp.content)

        # convert response from the bottom pod
        # for different version.
        response.status = b_status
        if b_status == 200:
            if b_body_ret.get('metadata') is not None:
                b_metadata_ret = b_body_ret['metadata']

                sps_ret = hclient.convert_object(b_release,
                                                 t_release,
                                                 b_metadata_ret,
                                                 res_type=cons.
                                                 RT_VOl_METADATA)

                return {'metadata': sps_ret}

        return b_body_ret

    @expose(generic=True, template='json')
    def get_one(self):
        """Get all metadata associated with a snapshot."""
        context = t_context.extract_context_from_environ()
        t_release = cons.R_MITAKA
        b_release = cons.R_MITAKA

        b_headers = hclient.convert_header(t_release,
                                           b_release,
                                           request.headers)

        try:
            mappings = db_api.get_bottom_mappings_by_top_id(context,
                                                            self.snapshot_id,
                                                            cons.RT_SNAPSHOT)
            if not mappings:
                return utils.format_cinder_error(
                    404,
                    _('snapshot %s could not be found.') % self.snapshot_id)
            pod = mappings[0][0]
            if not pod:
                return utils.format_cinder_error(
                    404,
                    _('snapshot %s could not be found.') % self.snapshot_id)
            s_ctx = hclient.get_pod_service_ctx(
                context,
                request.url,
                pod['pod_name'],
                s_type=cons.ST_CINDER)
            if not s_ctx:
                return utils.format_cinder_error(
                    500, _('Fail to find resource'))
        except Exception as e:
            LOG.exception(_('Fail to get metadata for a snapshot:'
                            '%(snapshot_id)s'
                            '%(exception)s'),
                          {'snapshot_id': self.snapshot_id,
                           'exception': e})
            return utils.format_cinder_error(
                500,
                _('Fail to get metadata'))

        resp = hclient.forward_req(context, 'GET',
                                   b_headers,
                                   s_ctx['b_url'],
                                   request.body)

        b_body_ret = jsonutils.loads(resp.content)

        b_status = resp.status_code
        response.status = b_status
        if b_status == 200:
            if b_body_ret.get('metadata') is not None:
                b_metadata_ret = b_body_ret['metadata']
                vol_ret = hclient.convert_object(
                    b_release, t_release,
                    b_metadata_ret,
                    res_type=cons.RT_VOl_METADATA)

                return {'metadata': vol_ret}

        return b_body_ret

    @expose(generic=True, template='json')
    def put(self, **kw):
        context = t_context.extract_context_from_environ()
        if 'metadata' not in kw:
            return utils.format_cinder_error(
                400, _("Missing required element 'metadata' in "
                       "request body."))

        t_release = cons.R_MITAKA
        b_release = cons.R_MITAKA

        try:
            mappings = db_api.get_bottom_mappings_by_top_id(
                context,
                self.snapshot_id,
                cons.RT_SNAPSHOT)

            if not mappings:
                return utils.format_cinder_error(
                    404,
                    _('snapshot %s could not be found.') %
                    self.snapshot_id)
            pod = mappings[0][0]
            if not pod:
                return utils.format_cinder_error(
                    404,
                    _('snapshot %s could not be found.') %
                    self.snapshot_id)
            s_ctx = hclient.get_pod_service_ctx(
                context,
                request.url,
                pod['pod_name'],
                s_type=cons.ST_CINDER)
            if not s_ctx:
                return utils.format_cinder_error(
                    404, _('Resource not found'))
        except Exception as e:
            LOG.exception(
                _('Fail to update metadata for a snapshot: '
                  '%(snapshot_id)s'
                  '%(exception)s'),
                {'snapshot_id': self.snapshot_id,
                 'exception': e})
            return utils.format_cinder_error(
                500, _('Fail to update metadata'))

        b_headers = hclient.convert_header(t_release,
                                           b_release,
                                           request.headers)

        t_metadata = kw['metadata']

        # add or remove key/value in the request for diff. version
        b_vol_req = hclient.convert_object(
            t_release,
            b_release,
            t_metadata,
            res_type=cons.RT_VOl_METADATA)

        b_body = jsonutils.dumps({'metadata': b_vol_req})

        resp = hclient.forward_req(context, 'PUT',
                                   b_headers,
                                   s_ctx['b_url'],
                                   b_body)

        b_status = resp.status_code
        b_body_ret = jsonutils.loads(resp.content)
        response.status = b_status

        if b_status == 200:
            if b_body_ret.get('metadata') is not None:
                b_metadata_ret = b_body_ret['metadata']
                vol_ret = hclient.convert_object(
                    b_release, t_release,
                    b_metadata_ret,
                    res_type=cons.RT_VOl_METADATA)
                return {'metadata': vol_ret}

        return b_body_ret

    @expose(generic=True, template='json')
    def delete(self, key):
        """Delete the given metadata item from a snapshot."""
        context = t_context.extract_context_from_environ()

        t_release = cons.R_MITAKA
        b_release = cons.R_MITAKA

        try:
            mappings = db_api.get_bottom_mappings_by_top_id(
                context,
                self.snapshot_id,
                cons.RT_SNAPSHOT)
            if not mappings:
                return utils.format_cinder_error(
                    404,
                    _('snapshot %s could not be found.') %
                    self.snapshot_id)
            pod = mappings[0][0]
            if not pod:
                return utils.format_cinder_error(
                    404,
                    _('snapshot %s could not be found.') %
                    self.snapshot_id)
            s_ctx = hclient.get_pod_service_ctx(
                context,
                request.url,
                pod['pod_name'],
                s_type=cons.ST_CINDER)
            if not s_ctx:
                return utils.format_cinder_error(
                    404, _('Fail to find resource'))
        except Exception as e:
            LOG.exception(
                _LE('Fail to delete metadata from a snapshot: '
                    '%(snapshot_id)s'
                    '%(exception)s'),
                {'snapshot_id': self.snapshot_id,
                 'exception': e})
            return utils.format_cinder_error(
                500, _('Fail to delete metadata'))

        if s_ctx['b_url'] == '':
            return utils.format_cinder_error(
                500, _('Bottom pod endpoint incorrect'))

        b_headers = hclient.convert_header(t_release,
                                           b_release,
                                           request.headers)

        resp = hclient.forward_req(context,
                                   'DELETE',
                                   b_headers,
                                   s_ctx['b_url'],
                                   request.body)

        response.status = resp.status_code
        # don't remove the resource routing for delete is async. operation
        # remove the routing when query is executed but not found
        # No content in the resp actually
        return response
