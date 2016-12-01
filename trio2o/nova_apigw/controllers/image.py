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

from pecan import expose
from pecan import rest

import trio2o.common.client as t_client
from trio2o.common import constants
import trio2o.common.context as t_context
from trio2o.common.i18n import _
from trio2o.common import utils
import trio2o.db.api as db_api


class ImageController(rest.RestController):

    def __init__(self, project_id):
        self.project_id = project_id
        self.client = t_client.Client()

    def _get_links(self, context, image):
        nova_url = self.client.get_endpoint(
            context, db_api.get_top_pod(context)['pod_id'],
            constants.ST_NOVA)
        nova_url = nova_url.replace('/$(tenant_id)s', '')
        self_link = utils.url_join(nova_url, self.project_id,
                                   'images', image['id'])
        bookmark_link = utils.url_join(
            utils.remove_trailing_version_from_href(nova_url),
            self.project_id, 'images', image['id'])
        glance_url = self.client.get_endpoint(
            context, db_api.get_top_pod(context)['pod_id'],
            constants.ST_GLANCE)
        alternate_link = '/'.join([glance_url, 'images', image['id']])
        return [{'rel': 'self', 'href': self_link},
                {'rel': 'bookmark', 'href': bookmark_link},
                {'rel': 'alternate',
                        'type': 'application/vnd.openstack.image',
                        'href': alternate_link}]

    @staticmethod
    def _format_date(dt):
        """Return standard format for a given datetime string."""
        if dt is not None:
            date_string = dt.split('.')[0]
            date_string += 'Z'
            return date_string

    @staticmethod
    def _get_status(image):
        """Update the status field to standardize format."""
        return {
            'active': 'ACTIVE',
            'queued': 'SAVING',
            'saving': 'SAVING',
            'deleted': 'DELETED',
            'pending_delete': 'DELETED',
            'killed': 'ERROR',
        }.get(image.get('status'), 'UNKNOWN')

    @staticmethod
    def _get_progress(image):
        return {
            'queued': 25,
            'saving': 50,
            'active': 100,
        }.get(image.get('status'), 0)

    def _construct_list_image_entry(self, context, image):
        return {'id': image['id'],
                'name': image.get('name'),
                'links': self._get_links(context, image)}

    def _construct_show_image_entry(self, context, image):
        return {
            'id': image['id'],
            'name': image.get('name'),
            'minRam': int(image.get('min_ram') or 0),
            'minDisk': int(image.get('min_disk') or 0),
            'metadata': image.get('properties', {}),
            'created': self._format_date(image.get('created_at')),
            'updated': self._format_date(image.get('updated_at')),
            'status': self._get_status(image),
            'progress': self._get_progress(image),
            'links': self._get_links(context, image)
        }

    @expose(generic=True, template='json')
    def get_one(self, _id):
        context = t_context.extract_context_from_environ()
        if _id == 'detail':
            return self.get_all()
        image = self.client.get_images(context, _id)
        if not image:
            return utils.format_nova_error(404, _('Image not found'))
        return {'image': self._construct_show_image_entry(context, image)}

    @expose(generic=True, template='json')
    def get_all(self):
        context = t_context.extract_context_from_environ()
        images = self.client.list_images(context)
        ret_images = [self._construct_list_image_entry(
            context, image) for image in images]
        return {'images': ret_images}
