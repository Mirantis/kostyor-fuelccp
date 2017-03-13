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


# Kubernetes PODs may consist of one or more containers, and therefore
# run one or more OpenStack services. In order to figure out which services
# are running inside some POD, we use the following dictionary that maps
# CCP application name onto a list of OpenStack services.
_SERVICES_BY_APP = {
    'keystone': [
        'keystone-wsgi-admin',
        'keystone-wsgi-public',
    ],
    'glance-api': [
        'glance-api',
    ],
    'glance-registry': [
        'glance-registry',
    ],
    'nova-api': [
        'nova-api',
    ],
    'nova-compute': [
        'nova-compute',
    ],
    'nova-compute-ironic': [
        'nova-compute',
    ],
    'nova-conductor': [
        'nova-conductor',
    ],
    'nova-consoleauth': [
        'nova-consoleauth',
    ],
    'nova-novncproxy': [
        'nova-novncproxy',
    ],
    'nova-scheduler': [
        'nova-scheduler',
    ],
    'placement-api': [
        'placement-api',
    ],
    'neutron-dhcp-agent': [
        'neutron-dhcp-agent',
    ],
    'neutron-l3-agent': [
        'neutron-l3-agent',
    ],
    'neutron-l3-agent-compute': [
        'neutron-l3-agent',
    ],
    'neutron-metadata-agent': [
        'neutron-metadata-agent',
    ],
    'neutron-openvswitch-agent': [
        'neutron-openvswitch-agent',
    ],
    'neutron-server': [
        'neutron-server',
    ],
    'neutron-sriov-nic-agent': [
        'neutron-sriov-nic-agent',
    ],
    'cinder-api': [
        'cinder-api',
    ],
    'cinder-backup': [
        'cinder-backup',
    ],
    'cinder-scheduler': [
        'cinder-scheduler',
    ],
    'cinder-volume': [
        'cinder-volume',
    ],
    'horizon': [
        'horizon-wsgi',
    ],
    'heat-api': [
        'heat-api',
    ],
    'heat-api-cfn': [
        'heat-api-cfn',
    ],
    'heat-engine': [
        'heat-engine',
    ],
    'ironic-api': [
        'ironic-api',
    ],
    'ironic-conductor': [
        'ironic-conductor',
    ],
    'murano-api': [
        'murano-api',
    ],
    'murano-engine': [
        'murano-engine',
    ],
    'sahara-api': [
        'sahara-api',
    ],
    'sahara-engine': [
        'sahara-engine',
    ],
}

# If for discovering we need to figure out which services are running by
# PODs, for upgrade procedure we need to do vice versa. THe reason behind
# is that we want to ensure that each application is upgraded only once,
# and mapping a service onto application helps to implement this tracking.
_APP_BY_SERVICE = {
    service: app
    for app, services in _SERVICES_BY_APP.items()
    for service in services
}


def get_services_by_app(appname):
    return _SERVICES_BY_APP.get(appname)


def get_app_by_service(service_name):
    return _APP_BY_SERVICE.get(service_name)
