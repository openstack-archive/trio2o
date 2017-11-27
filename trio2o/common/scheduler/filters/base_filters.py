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

from oslo_log import log as logging

from trio2o.common import loadables

LOG = logging.getLogger(__name__)


class BaseFilter(object):
    """Base class for all pod filter classes."""
    def _filter_one(self, context, obj, filter_properties):
        return True

    def filter_all(self, context, filter_obj_list, filter_properties):
        for obj in filter_obj_list:
            if self._filter_one(context, obj, filter_properties):
                yield obj


class BaseFilterHandler(loadables.BaseLoader):
    """Base class to handle loading filter classes.

    This class should be subclassed where one needs to use filters.
    """

    def get_filtered_objects(self, context, filters, objs, spec_obj):
        list_objs = list(objs)
        LOG.debug("Starting with %d pod(s)", len(list_objs))

        for filter_ in filters:
            cls_name = filter_.__class__.__name__

            objs = filter_.filter_all(context, list_objs, spec_obj)
            if objs is None:
                LOG.debug("Filter %s says to stop filtering", cls_name)
                return
            list_objs = list(objs)
        return list_objs
