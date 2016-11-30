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
from pecan import rest

from oslo_log import log as logging
from oslo_serialization import jsonutils

from trio2o.common import constants as cons
import trio2o.common.context as t_context
from trio2o.common import httpclient as hclient
from trio2o.common.i18n import _
from trio2o.common import utils

import trio2o.db.api as db_api

LOG = logging.getLogger(__name__)


class VolumeBackupController(rest.RestController):
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id

    @expose(generic=True, template='json')
    def post(self, **kwargs):
        context = t_context.extract_context_from_environ()

        if 'backup' not in kwargs:
            return utils.format_cinder_error(
                400, _("Missing required element 'backup' in request body."))

        volume_id = kwargs['backup']['volume_id']
        volume_mappings = db_api.get_bottom_mappings_by_top_id(
            context, volume_id, cons.RT_VOLUME)
        if not volume_mappings:
            return utils.format_cinder_error(
                404, _('Volume %(volume_id)s could not be found.') % {
                    'volume_id': volume_id
                })

        pod_name = volume_mappings[0][0]['pod_name']

        t_release = cons.R_MITAKA
        b_release = cons.R_MITAKA

        s_ctx = hclient.get_pod_service_ctx(
            context,
            request.url,
            pod_name,
            s_type=cons.ST_CINDER)

        b_headers = hclient.convert_header(t_release,
                                           b_release,
                                           request.headers)
        t_vol = kwargs['backup']
        b_vol_req = hclient.convert_object(t_release, b_release, t_vol,
                                           res_type=cons.RT_BACKUP)
        b_body = jsonutils.dumps({'backup': b_vol_req})

        resp = hclient.forward_req(
            context,
            'POST',
            b_headers,
            s_ctx['b_url'],
            b_body)
        b_status = resp.status_code
        b_ret_body = jsonutils.loads(resp.content)
        resp.status = b_status
        if b_status == 200:
            if b_ret_body.get('backup') is not None:
                b_backup_ret = b_ret_body['backup']

                vol_ret = hclient.convert_object(b_release, t_release,
                                                 b_backup_ret,
                                                 res_type=cons.
                                                 RT_BACKUP)

                return {'backup': vol_ret}

        return b_ret_body
