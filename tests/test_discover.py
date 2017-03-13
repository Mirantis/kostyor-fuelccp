# Copyright 2017 Mirantis
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock
import pytest

from kostyor.rpc import app
from kostyor_fuelccp import discover

from .common import get_fixture


class TestDriver(object):

    _pods = get_fixture('ccppods.json')

    @pytest.fixture(autouse=True)
    def use_sync_tasks(self, monkeypatch):
        monkeypatch.setattr(app.app.conf, 'CELERY_ALWAYS_EAGER', True)

    @pytest.fixture(autouse=True)
    def use_fake_response(self, monkeypatch):
        monkeypatch.setattr(
            'kostyor_fuelccp.discover.pykube.HTTPClient.get',
            mock.Mock(
                return_value=mock.Mock(
                    json=mock.Mock(return_value=self._pods)
                )
            )
        )

    def test_discover(self):
        info = discover.Driver().discover()

        # We don't care about services order within a node as long as every
        # service is detected. So let's sort loaded data so it won't affect
        # assert below.
        for hostname, services in info['hosts'].items():
            info['hosts'][hostname] = sorted(services, key=lambda v: v['name'])

        assert info == {
            'hosts': {
                'ikalnitsky-k8s-2': [
                    {'name': 'glance-api'},
                    {'name': 'glance-registry'},
                    {'name': 'heat-api'},
                    {'name': 'heat-api-cfn'},
                    {'name': 'heat-engine'},
                    {'name': 'horizon-wsgi'},
                    {'name': 'keystone-wsgi-admin'},
                    {'name': 'keystone-wsgi-public'},
                    {'name': 'neutron-dhcp-agent'},
                    {'name': 'neutron-l3-agent'},
                    {'name': 'neutron-metadata-agent'},
                    {'name': 'neutron-openvswitch-agent'},
                    {'name': 'neutron-server'},
                    {'name': 'nova-api'},
                    {'name': 'nova-conductor'},
                    {'name': 'nova-consoleauth'},
                    {'name': 'nova-novncproxy'},
                    {'name': 'nova-scheduler'},
                ],
                'ikalnitsky-k8s-3': [
                    {'name': 'neutron-openvswitch-agent'},
                    {'name': 'nova-compute'},
                ],
                'ikalnitsky-k8s-4': [
                    {'name': 'neutron-openvswitch-agent'},
                    {'name': 'nova-compute'},
                ],
            }
        }
