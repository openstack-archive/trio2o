# Copyright 2015 Huawei Technologies Co., Ltd.
# All Rights Reserved
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

import trio2o.common.client

# Todo: adding rpc cap negotiation configuration after first release
# import trio2o.common.xrpcapi


def list_opts():
    return [
        ('client', trio2o.common.client.client_opts),
        # ('upgrade_levels', trio2o.common.xrpcapi.rpcapi_cap_opt),
    ]
