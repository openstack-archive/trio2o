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


class BaseFilter(object):
    """Base class for all pod filter classes."""
    def _filter_one(self, context, obj, filter_properties):
        return True

    def filter_all(self, context, filter_obj_list, filter_properties):
        for obj in filter_obj_list:
            if self._filter_one(context, obj, filter_properties):
                yield obj


class BasePodFilter(BaseFilter):

    def _filter_one(self, context, pod, filter_properties):
        return self.is_pod_passed(context, pod, filter_properties)

    def is_pod_passed(self, context, pod, filter_properties):
        """Return True if the pod passes the filter, otherwise False.

        """
        raise NotImplementedError()
