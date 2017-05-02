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
from trio2o.db import core
from trio2o.db import models

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
