# Copyright (c) 2016 Huawei Technologies Co., Ltd.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from tempest.lib import decorators

from trio2o.tempestplugin.tests.api import base


class TestTrio2oSample(base.BaseTrio2oTest):

    @classmethod
    def resource_setup(cls):
        super(TestTrio2oSample, cls).resource_setup()

    @decorators.attr(type="smoke")
    def test_sample(self):
        self.assertEqual('Trio2o Sample Test!', 'Trio2o Sample Test!')

    @classmethod
    def resource_cleanup(cls):
        super(TestTrio2oSample, cls).resource_cleanup()
