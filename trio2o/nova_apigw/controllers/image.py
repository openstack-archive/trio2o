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

SUPPORTED_FILTERS = {
    'name': 'name',
    'status': 'status',
    'changes-since': 'changes-since',
    'server': 'property-instance_uuid',
    'type': 'property-image_type',
    'minRam': 'min_ram',
    'minDisk': 'min_disk',
}


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
            'created': image.get('created_at'),
            'updated': image.get('updated_at'),
            'status': self._get_status(image),
            'progress': self._get_progress(image),
            'links': self._get_links(context, image)
        }

    @expose(generic=True, template='json')
    def get_one(self, _id, **kwargs):
        context = t_context.extract_context_from_environ()
        if _id == 'detail':
            return self.get_all(**kwargs)
        image = self.client.get_images(context, _id)
        if not image:
            return utils.format_nova_error(404, _('Image not found'))
        return {'image': self._construct_show_image_entry(context, image)}

    @expose(generic=True, template='json')
    def get_all(self, **kwargs):
        context = t_context.extract_context_from_environ()
        filters = self._get_filters(kwargs)
        filters = [{'key': key,
                    'comparator': 'eq',
                    'value': value} for key, value in filters.iteritems()]
        images = self.client.list_images(context, filters=filters)
        ret_images = [self._construct_list_image_entry(
            context, image) for image in images]
        return {'images': ret_images}

    def _get_filters(self, params):
        """Return a dictionary of query param filters from the request.

        :param params: the URI params coming from the wsgi layer
        :return a dict of key/value filters
        """
        filters = {}
        for param in params:
            if param in SUPPORTED_FILTERS or param.startswith('property-'):
                # map filter name or carry through if property-*
                filter_name = SUPPORTED_FILTERS.get(param, param)
                filters[filter_name] = params.get(param)

        # ensure server filter is the instance uuid
        filter_name = 'property-instance_uuid'
        try:
            filters[filter_name] = filters[filter_name].rsplit('/', 1)[1]
        except (AttributeError, IndexError, KeyError):
            pass

        filter_name = 'status'
        if filter_name in filters:
            # The Image API expects us to use lowercase strings for status
            filters[filter_name] = filters[filter_name].lower()

        return filters
