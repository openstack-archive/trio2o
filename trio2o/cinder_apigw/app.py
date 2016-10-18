# Copyright (c) 2015 Huawei, Tech. Co,. Ltd.
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

import pecan

from oslo_config import cfg

from trio2o.common.i18n import _
from trio2o.common import restapp


common_opts = [
    cfg.IPOpt('bind_host', default='0.0.0.0',
              help=_("The host IP to bind to")),
    cfg.PortOpt('bind_port', default=19997,
                help=_("The port to bind to")),
    cfg.IntOpt('api_workers', default=1,
               help=_("number of api workers")),
    cfg.StrOpt('api_extensions_path', default="",
               help=_("The path for API extensions")),
    cfg.StrOpt('auth_strategy', default='keystone',
               help=_("The type of authentication to use")),
    cfg.BoolOpt('allow_bulk', default=True,
                help=_("Allow the usage of the bulk API")),
    cfg.BoolOpt('allow_pagination', default=False,
                help=_("Allow the usage of the pagination")),
    cfg.BoolOpt('allow_sorting', default=False,
                help=_("Allow the usage of the sorting")),
    cfg.StrOpt('pagination_max_limit', default="-1",
               help=_("The maximum number of items returned in a single "
                      "response, value was 'infinite' or negative integer "
                      "means no limit")),
]


def setup_app(*args, **kwargs):
    config = {
        'server': {
            'port': cfg.CONF.bind_port,
            'host': cfg.CONF.bind_host
        },
        'app': {
            'root': 'trio2o.cinder_apigw.controllers.root.RootController',
            'modules': ['trio2o.cinder_apigw'],
            'errors': {
                400: '/error',
                '__force_dict__': True
            }
        }
    }
    pecan_config = pecan.configuration.conf_from_dict(config)

    # app_hooks = [], hook collection will be put here later

    app = pecan.make_app(
        pecan_config.app.root,
        debug=False,
        wrap_app=restapp.auth_app,
        force_canonical=False,
        hooks=[],
        guess_content_type_from_ext=True
    )

    return app
