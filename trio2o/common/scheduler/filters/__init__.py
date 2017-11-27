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

from trio2o.common.scheduler.filters import base_filters


class BasePodFilter(base_filters.BaseFilter):

    def _filter_one(self, context, pod, filter_properties):
        return self.is_pod_passed(context, pod, filter_properties)

    def is_pod_passed(self, context, pod, filter_properties):
        """Return True if the pod passes the filter, otherwise False.

        """
        raise NotImplementedError()


class PodFilterHandler(base_filters.BaseFilterHandler):
    def __init__(self):
        super(PodFilterHandler, self).__init__(BasePodFilter)


def all_filters():
    """Return a list of filter classes found in this directory.

    This method is used as the default for available scheduler filters
    and should return a list of all filter classes available.
    """
    return PodFilterHandler().get_all_classes()
