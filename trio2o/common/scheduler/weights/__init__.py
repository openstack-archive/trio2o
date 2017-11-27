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

from trio2o.common.scheduler.weights import base_weights


class WeighedPod(base_weights.WeighedObject):
    def to_dict(self):
        x = dict(weight=self.weight)
        x['pod_state_obj'] = self.obj
        return x

    def __repr__(self):
        return "WeighedPod [pod_state: %r, weight: %s]" % (
            self.obj, self.weight)


class BasePodWeigher(base_weights.BaseWeigher):
    """Base class for pod weights."""
    pass


class PodWeightHandler(base_weights.BaseWeightHandler):
    object_class = WeighedPod

    def __init__(self):
        super(PodWeightHandler, self).__init__(BasePodWeigher)


def all_weighers():
    """Return a list of weight plugin classes found in this directory."""
    return PodWeightHandler().get_all_classes()
