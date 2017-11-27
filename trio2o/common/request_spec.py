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


class RequestSpec(object):
    # request object that saves the request parameters from client, then
    # it's used to choose pod from a list of pods
    def __init__(self, project_id,
                 requested_destination=None,
                 ignore_pods=[],
                 az_name=None,
                 affinity_tags={},
                 load_sensitive=None,
                 time_sensitive=None,
                 create_time=None,
                 vcpus=None,
                 memory_mb=None,
                 disk_gb=None):
        self.project_id = project_id
        self.requested_destination = requested_destination
        self.ignore_pods = ignore_pods or []
        self.az_name = az_name
        self.affinity_tags = affinity_tags or {}
        self.load_sensitive = load_sensitive
        self.time_sensitive = time_sensitive
        self.create_time = create_time
        self.vcpus = vcpus
        self.memory_mb = memory_mb
        self.disk_gb = disk_gb

    def to_dict(self):
        request_spec_dict = {
            'requested_destination': self.requested_destination,
            'ignore_pods': self.ignore_pods,
            'az_name': self.az_name,
            'project_id': self.project_id,
            'affinity_tags': self.affinity_tags,
            'load_sensitive': self.load_sensitive,
            'time_sensitive': self.time_sensitive,
            'create_time': self.create_time,
            'vcpus': self.vcpus,
            'memory_mb': self.memory_mb,
            'disk_gb': self.disk_gb,
        }

        return request_spec_dict
