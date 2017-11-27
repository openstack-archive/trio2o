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
import pecan
from pecan.configuration import set_config
from pecan.testing import load_test_app

from oslo_config import cfg
from oslo_config import fixture as fixture_config

from trio2o.api import app
from trio2o.common import az_ag  # noqa
from trio2o.common import context
from trio2o.common import policy
from trio2o.db import core
from trio2o.tests import base


OPT_GROUP_NAME = 'keystone_authtoken'
cfg.CONF.import_group(OPT_GROUP_NAME, "keystonemiddleware.auth_token")


def fake_admin_context():
    context_paras = {'is_admin': True}
    return context.Context(**context_paras)


def fake_non_admin_context():
    context_paras = {}
    return context.Context(**context_paras)


class API_FunctionalTest(base.TestCase):

    def setUp(self):
        super(API_FunctionalTest, self).setUp()

        self.addCleanup(set_config, {}, overwrite=True)

        cfg.CONF.clear()
        cfg.CONF.register_opts(app.common_opts)

        self.CONF = self.useFixture(fixture_config.Config()).conf

        self.CONF.set_override('auth_strategy', 'noauth')
        self.CONF.set_override('trio2o_db_connection', 'sqlite:///:memory:')

        core.initialize()
        core.ModelBase.metadata.create_all(core.get_engine())

        self.context = context.get_admin_context()

        policy.populate_default_rules()

        self.app = self._make_app()

    def _make_app(self, enable_acl=False):
        self.config = {
            'app': {
                'root': 'trio2o.api.controllers.root.RootController',
                'modules': ['trio2o.api'],
                'enable_acl': enable_acl,
                'errors': {
                    400: '/error',
                    '__force_dict__': True
                }
            },
        }

        return load_test_app(self.config)

    def tearDown(self):
        super(API_FunctionalTest, self).tearDown()
        cfg.CONF.unregister_opts(app.common_opts)
        pecan.set_config({}, overwrite=True)
        core.ModelBase.metadata.drop_all(core.get_engine())
        policy.reset()


class TestPodAffinityTagController(API_FunctionalTest):
    """Test version listing on root URI."""

    @patch.object(context, 'extract_context_from_environ',
                  new=fake_admin_context)
    def test_post_no_input(self):
        pod_affinity_tags = [
            # missing pod-affinity-tag
            {
                "pod_affinity_tag_xxx":
                {
                    "key": "volume",
                    "value": "SSD",
                    "pod_id": ""
                },
                "expected_error": 400
            }]

        for test_pod_affinity_tag in pod_affinity_tags:
            response = self.app.post_json(
                '/v1.0/pod-affinity-tag',
                dict(tag_xxx=test_pod_affinity_tag['pod_affinity_tag_xxx']),
                expect_errors=True)

            self.assertEqual(response.status_int,
                             test_pod_affinity_tag['expected_error'])

    @patch.object(context, 'extract_context_from_environ',
                  new=fake_admin_context)
    def test_post_invalid_input(self):
        pod_affinity_tags = [
            # value is empty
            {
                "pod_affinity_tag":
                    {
                        "key": "volume",
                        "value": ""
                    },
                "expected_error": 400
            },

            # key is empty
            {
                "pod_affinity_tag":
                    {
                        "key": "",
                        "value": "SSD"
                    },
                "expected_error": 400
            },

            # pod_id is empty
            {
                "pod_affinity_tag":
                    {
                        "key": "volume",
                        "value": "SSD",
                        "pod_id": ""
                    },
                "expected_error": 400
            },
            ]

        self._test_and_check_pod_affinity_tag(pod_affinity_tags)

    @patch.object(context, 'extract_context_from_environ',
                  new=fake_admin_context)
    def test_post(self):
        pod_affinity_tags = [
            {
                "pod_affinity_tag":
                    {
                        "key": "volume",
                        "value": "SSD",
                        "pod_id": "pod_id_12345"
                    },
                "expected_error": 200
            },
        ]

        self._test_and_check_pod_affinity_tag(pod_affinity_tags)

    def _test_and_check_pod_affinity_tag(self, pod_affinity_tags):

        for pod_affinity_tag in pod_affinity_tags:
            response = self.app.post_json(
                '/v1.0/pod-affinity-tag',
                dict(
                    pod_affinity_tag=pod_affinity_tag['pod_affinity_tag']),
                expect_errors=True)
            self.assertEqual(response.status_int,
                             pod_affinity_tag['expected_error'])

    @patch.object(context, 'extract_context_from_environ',
                  new=fake_admin_context)
    def test_get_all(self):

        pod_affinity_tags = [
            {
                "pod_affinity_tag":
                    {
                        "key": "volume",
                        "value": "SSD",
                        "pod_id": "pod_id_12345"
                    },
                "expected_error": 200
            },
            {
                "pod_affinity_tag":
                    {
                        "key": "load_type",
                        "value": "Container",
                        "pod_id": "pod_id_12346"
                    },
                "expected_error": 200
            },
        ]

        self._test_and_check_pod_affinity_tag(pod_affinity_tags)

        response = self.app.get('/v1.0/pod-affinity-tag')
        affinity_tag_count = 2
        self.assertEqual(affinity_tag_count,
                         len(response.json['pod_affinity_tag']))

    @patch.object(context, 'extract_context_from_environ',
                  new=fake_admin_context)
    def test_get_delete_one(self):

        pod_affinity_tags = [
            {
                "pod_affinity_tag":
                    {
                        "key": "volume",
                        "value": "SSD",
                        "pod_id": "pod_id_12345"
                    },
                "expected_error": 200
            },
            {
                "pod_affinity_tag":
                    {
                        "key": "load_type",
                        "value": "Container",
                        "pod_id": "pod_id_12346"
                    },
                "expected_error": 200
            },
        ]

        self._test_and_check_pod_affinity_tag(pod_affinity_tags)

        response = self.app.get('/v1.0/pod-affinity-tag')
        return_tags = response.json

        for ret_pod_tag in return_tags['pod_affinity_tag']:

            _id = ret_pod_tag['affinity_tag_id']
            single_ret = self.app.get('/v1.0/pod-affinity-tag/' + str(_id))

            self.assertEqual(single_ret.status_int, 200)

            one_tag_ret = single_ret.json
            get_one_tag = one_tag_ret['pod_affinity_tag']

            self.assertEqual(get_one_tag['affinity_tag_id'],
                             ret_pod_tag['affinity_tag_id'])

            self.assertEqual(get_one_tag['key'],
                             ret_pod_tag['key'])

            self.assertEqual(get_one_tag['value'],
                             ret_pod_tag['value'])

            self.assertEqual(get_one_tag['pod_id'],
                             ret_pod_tag['pod_id'])

            _id = ret_pod_tag['affinity_tag_id']
            ret = self.app.delete('/v1.0/pod-affinity-tag/' + str(_id),
                                  expect_errors=True)

            self.assertEqual(ret.status_int, 200)

            single_ret = self.app.get('/v1.0/pod-affinity-tag/' + str(_id),
                                      expect_errors=True)

            self.assertEqual(single_ret.status_int, 404)
