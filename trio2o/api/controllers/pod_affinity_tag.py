# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import pecan
from pecan import expose
from pecan import rest

from oslo_log import log as logging
from oslo_utils import uuidutils

import trio2o.common.context as t_context
import trio2o.common.exceptions as t_exc
from trio2o.common.i18n import _
from trio2o.common.i18n import _LE
from trio2o.common import policy
from trio2o.common import utils
from trio2o.db import api as db_api

LOG = logging.getLogger(__name__)


class PodAffinityTagController(rest.RestController):

    def __init__(self):
        pass

    @expose(generic=True, template='json')
    def post(self, **kw):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_AFFINITY_TAG_CREATE):
            return utils.format_nova_error(
                403, _("Unauthorized to pod affinity tag"))

        if 'pod_affinity_tag' not in kw:
            return utils.format_nova_error(
                400, _("Request body not found"))

        tag = kw['pod_affinity_tag']

        for field in ('key', 'value', 'pod_id'):
            value = tag.get(field)
            if value is None or len(value.strip()) == 0:
                return utils.format_nova_error(
                    400, _("Field %(field)s can not be empty") % {
                        'field': field})

        try:
            key = tag.get('key', '').strip()
            value = tag.get('value', '').strip()
            pod_id = tag.get('pod_id', '').strip()
            uuid = uuidutils.generate_uuid()

            tag_dict = {'pod_id': pod_id,
                        'key': key,
                        'value': value,
                        'affinity_tag_id': uuid}

            pod_tag = db_api.create_pod_affinity_tag(context, tag_dict)
            if not pod_tag:
                return utils.format_nova_error(
                    409, _('Pod affinity tag already exists'))
        except Exception as e:
            LOG.exception('Failed to create pod affinity tag: '
                          '%(exception)s ', {'exception': e})
            return utils.format_nova_error(
                500, _('Failed to create pod affinity tag'))

        return {'pod_affinity_tag': pod_tag}

    @expose(generic=True, template='json')
    def get_one(self, _id):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_AFFINITY_TAG_SHOW):
            return utils.format_nova_error(
                403, _("Unauthorized to show pod affinity tag"))

        try:
            return {'pod_affinity_tag': db_api.get_pod_affinity_tag(context,
                                                                    _id)}
        except t_exc.ResourceNotFound:
            return utils.format_nova_error(
                404, _("Pod affinity tag not found"))

    @expose(generic=True, template='json')
    def get_all(self):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_AFFINITY_TAG_LIST):
            return utils.format_nova_error(
                403, _("Unauthorized to list pod affinity tags"))

        try:
            return {'pod_affinity_tag': db_api.list_pod_affinity_tag(context)}
        except Exception as e:
            LOG.exception(_LE(
                'Failed to list all pod affinity tags: %(exception)s '),
                {'exception': e})

            return utils.format_nova_error(
                500, _("Failed to list pod affinity tags"))

    @expose(generic=True, template='json')
    def delete(self, _id):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_AFFINITY_TAG_DELETE):
            return utils.format_nova_error(
                403, _("Unauthorized to delete pod affinity tag"))

        try:
            db_api.get_pod_affinity_tag(context, _id)
        except t_exc.ResourceNotFound:
            return utils.format_nova_error(404,
                                           _('Pod affinity tag not found'))
        try:
            db_api.delete_pod_affinity_tag(context, _id)
            pecan.response.status = 200
            return {}
        except Exception as e:
            LOG.exception('Failed to delete the pod affinity tag: '
                          '%(exception)s ', {'exception': e})
            return utils.format_nova_error(
                500, _('Failed to delete the pod affinity tag'))
