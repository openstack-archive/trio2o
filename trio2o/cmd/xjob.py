# Copyright 2015 Huawei Technologies Co., Ltd.
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

# Much of this module is based on the work of the Ironic team
# see http://git.openstack.org/cgit/openstack/ironic/tree/ironic/cmd/api.py

import eventlet

if __name__ == "__main__":
    eventlet.monkey_patch()

import logging as std_logging
import sys

from oslo_config import cfg
from oslo_log import log as logging

from trio2o.common import config
from trio2o.common.i18n import _LI
from trio2o.common.i18n import _LW

from trio2o.xjob import xservice

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def main():
    config.init(xservice.common_opts, sys.argv[1:])

    host = CONF.host
    workers = CONF.workers

    if workers < 1:
        LOG.warning(_LW("Wrong worker number, worker = %(workers)s"), workers)
        workers = 1

    LOG.info(_LI("XJob Server on http://%(host)s with %(workers)s"),
             {'host': host, 'workers': workers})

    xservice.serve(xservice.create_service(), workers)

    LOG.info(_LI("Configuration:"))
    CONF.log_opt_values(LOG, std_logging.INFO)

    xservice.wait()

if __name__ == '__main__':
    main()
