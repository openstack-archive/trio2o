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

from trio2o.common.scheduler import filters
from trio2o.common.scheduler.filters import all_pods_filter
from trio2o.common.scheduler.filters import availability_zone_filter

import unittest


class PodFiltersTestCase(unittest.TestCase):

    def test_filter_handler(self):
        # Double check at least a couple of known filters exist
        filter_handler = filters.PodFilterHandler()
        classes = filter_handler.get_matching_classes(
            ['trio2o.common.scheduler.filters.all_filters'])
        self.assertIn(all_pods_filter.AllPodFilter, classes)
        self.assertIn(availability_zone_filter.AvailabilityZoneFilter, classes)
