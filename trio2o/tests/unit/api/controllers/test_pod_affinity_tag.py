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

from mock import patch
import unittest

from oslo_config import cfg
import pecan

from trio2o.api import app
from trio2o.api.controllers import pod
from trio2o.api.controllers import pod_affinity_tag
from trio2o.common import context
from trio2o.common import policy
from trio2o.db import api as db_api
from trio2o.db import core


class FakeResponse(object):
    def __new__(cls, code=500):
        cls.status = code
        cls.status_code = code
        return super(FakeResponse, cls).__new__(cls)


class PodAffinityTagControllerTest(unittest.TestCase):
    def setUp(self):
        super(PodAffinityTagControllerTest, self).setUp()

        cfg.CONF.clear()
        cfg.CONF.register_opts(app.common_opts)
        core.initialize()
        core.ModelBase.metadata.create_all(core.get_engine())
        self.controller = pod_affinity_tag.PodAffinityTagController()
        self.pod_controller = pod.PodsController()
        self.context = context.get_admin_context()
        policy.populate_default_rules()

    def _validate_error_code(self, res, code):
        self.assertEqual(res[list(res.keys())[0]]['code'], code)

    @patch.object(pecan, 'response', new=FakeResponse)
    @patch.object(context, 'extract_context_from_environ')
    def test_post(self, mock_context):
        mock_context.return_value = self.context

        kw = {'pod': {'pod_name': 'BottomPod', 'az_name': 'TopAZ'}}
        pod_id1 = self.pod_controller.post(**kw)['pod']['pod_id']
        pod_affinity_tag1 = self._prepare_pod_affinity_tag_element(pod_id1,
                                                                   "volume",
                                                                   "SSD")
        pod_affinity_tag2 = self.controller.post(**pod_affinity_tag1)
        id = pod_affinity_tag2['pod_affinity_tag']['affinity_tag_id']
        pod_affinity_tag3 = db_api.get_pod_affinity_tag(self.context, id)

        self.assertEqual('volume', pod_affinity_tag3['key'])
        self.assertEqual('SSD', pod_affinity_tag3['value'])

        pod_affinity_tag4 = db_api.list_pod_affinity_tag(self.context,
                                                         [{'key': 'volume',
                                                           'comparator': 'eq',
                                                           'value': 'SSD'
                                                           },
                                                          ])
        self.assertEqual(1, len(pod_affinity_tag4))

        # failure case, only admin can create pod affinity tag
        self.context.is_admin = False
        pod_affinity_tag5 = self._prepare_pod_affinity_tag_element(pod_id1,
                                                                   "volume",
                                                                   "SSD2")
        res = self.controller.post(**pod_affinity_tag5)
        self._validate_error_code(res, 403)

        self.context.is_admin = True

        # failure case, request body not found
        pod_affinity_tag6 = {'pod-affinity': {'key': "volume", 'value': "SSD"}}
        res = self.controller.post(**pod_affinity_tag6)
        self._validate_error_code(res, 400)

        # failure case, value in pod affinity tag is empty
        pod_affinity_tag7 = self._prepare_pod_affinity_tag_element(pod_id1,
                                                                   "volume",
                                                                   "SSD")
        pod_affinity_tag7['pod_affinity_tag'].update({'value': ''})
        res = self.controller.post(**pod_affinity_tag7)
        self._validate_error_code(res, 400)

        # failure case, value in pod affinity tag is 'None'
        pod_affinity_tag8 = self._prepare_pod_affinity_tag_element(pod_id1,
                                                                   "volume",
                                                                   "SSD")
        pod_affinity_tag8['pod_affinity_tag'].update({'value': None})
        res = self.controller.post(**pod_affinity_tag8)
        self._validate_error_code(res, 400)

    @patch.object(pecan, 'response', new=FakeResponse)
    @patch.object(context, 'extract_context_from_environ')
    def test_get_one(self, mock_context):
        mock_context.return_value = self.context

        kw = {'pod': {'pod_name': 'BottomPod', 'az_name': 'TopAZ'}}
        pod_id1 = self.pod_controller.post(**kw)['pod']['pod_id']
        pod_affinity_tag1 = self._prepare_pod_affinity_tag_element(pod_id1,
                                                                   "volume",
                                                                   "SSD")
        pod_affinity_tag2 = self.controller.post(**pod_affinity_tag1)
        id = pod_affinity_tag2['pod_affinity_tag']['affinity_tag_id']

        pod_affinity_tag3 = self.controller.get_one(id)
        self.assertEqual('SSD', pod_affinity_tag3['pod_affinity_tag']['value'])

        # failure case, only admin can get pod affinity tag
        self.context.is_admin = False
        res = self.controller.get_one(id)
        self._validate_error_code(res, 403)

        self.context.is_admin = True

        # failure case, pod affinity tag not found
        res = self.controller.get_one(-123)
        self._validate_error_code(res, 404)

    @patch.object(pecan, 'response', new=FakeResponse)
    @patch.object(context, 'extract_context_from_environ')
    def test_get_all(self, mock_context):
        mock_context.return_value = self.context

        kw = {'pod': {'pod_name': 'BottomPod', 'az_name': 'TopAZ_1'}}
        pod_id1 = self.pod_controller.post(**kw)['pod']['pod_id']
        pod_affinity_tag1 = self._prepare_pod_affinity_tag_element(pod_id1,
                                                                   "volume",
                                                                   "SSD")
        pod_affinity_tag2 = self._prepare_pod_affinity_tag_element(pod_id1,
                                                                   "load_type",
                                                                   "Container")
        self.controller.post(**pod_affinity_tag1)
        self.controller.post(**pod_affinity_tag2)

        pod_affinity_tags = self.controller.get_all()
        count_of_pod_tags = 2
        self.assertEqual(count_of_pod_tags,
                         len(pod_affinity_tags['pod_affinity_tag']))
        expect = ['SSD', 'Container']
        actual = [item['value']
                  for item in pod_affinity_tags['pod_affinity_tag']]
        self.assertEqual(expect, actual)

        # failure case, only admin can list pod affinity tags
        self.context.is_admin = False
        res = self.controller.get_all()
        self._validate_error_code(res, 403)

        self.context.is_admin = True

    @patch.object(pecan, 'response', new=FakeResponse)
    @patch.object(context, 'extract_context_from_environ')
    def test_delete(self, mock_context):
        mock_context.return_value = self.context

        kw = {'pod': {'pod_name': 'BottomPod', 'az_name': 'TopAZ'}}
        pod_id1 = self.pod_controller.post(**kw)['pod']['pod_id']

        pod_affinity_tag1 = self._prepare_pod_affinity_tag_element(pod_id1,
                                                                   "volume",
                                                                   "SSD")
        pod_affinity_tag2 = self.controller.post(**pod_affinity_tag1)
        id = pod_affinity_tag2['pod_affinity_tag']['affinity_tag_id']

        res = self.controller.delete(id)
        self.assertEqual({}, res)

        pod_affinity_tags = self.controller.get_all()
        self.assertEqual(0, len(pod_affinity_tags['pod_affinity_tag']))

        # failure case, only admin can delete pod affinity tag
        self.context.is_admin = False
        res = self.controller.delete(id)
        self._validate_error_code(res, 403)

        self.context.is_admin = True

        # failure case, pod affinity tag not found
        res = self.controller.delete(-123)
        self._validate_error_code(res, 404)

    def _prepare_pod_affinity_tag_element(self, pod_id, key, value):
        """Prepare an affinity tag for a pod

        :param pod_id: Create an affinity tag for pod $(pod_id)
        :return: A dictionary with key, value, pod_id, affinity_tag_id
        """
        fake_affinity_tag = {
            'pod_affinity_tag': {
                'pod_id': pod_id,
                'key': key,
                'value': value
            }
        }

        return fake_affinity_tag

    def tearDown(self):
        cfg.CONF.unregister_opts(app.common_opts)
        core.ModelBase.metadata.drop_all(core.get_engine())

        super(PodAffinityTagControllerTest, self).tearDown()
