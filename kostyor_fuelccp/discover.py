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

import collections

import pykube

from kostyor.inventory.discover import ServiceDiscovery
from kostyor.rpc.app import app


# PODs provided by Fuel CCP have an application label that uniquely
# defines which services the POD is running. This is a map of application
# label to OpenStack services.
_SERVICES_BY_CCPAPP = {
    'keystone': [
        'keystone-wsgi-admin',
        'keystone-wsgi-public',
    ],
    'glance-registry': [
        'glance-registry',
    ],
    'glance-api': [
        'glance-api',
    ],
    'nova-conductor': [
        'nova-conductor',
    ],
    'nova-scheduler': [
        'nova-scheduler',
    ],
    'nova-novncproxy': [
        'nova-novncproxy',
    ],
    'nova-consoleauth': [
        'nova-consoleauth',
    ],
    'nova-api': [
        'nova-api',
    ],
    'nova-compute': [
        'nova-compute',
    ],
    'neutron-server': [
        'neutron-server',
    ],
    'neutron-openvswitch-agent': [
        'neutron-openvswitch-agent',
    ],
    'neutron-l3-agent': [
        'neutron-l3-agent',
    ],
    'neutron-dhcp-agent': [
        'neutron-dhcp-agent',
    ],
    'neutron-metadata-agent': [
        'neutron-metadata-agent',
    ],
    'cinder-api': [
        'cinder-api',
    ],
    'cinder-scheduler': [
        'cinder-scheduler',
    ],
    'cinder-volume': [
        'cinder-volume',
    ],
    'cinder-backup': [
        'cinder-backup',
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
    'ironic-conductor': [
        'ironic-conductor',
    ],
    'ironic-api': [
        'ironic-api',
    ],
    'murano-api': [
        'murano-api',
    ],
    'murano-engine': [
        'murano-engine',
    ],
    'sahara-engine': [
        'sahara-engine',
    ],
    'sahara-api': [
        'sahara-api',
    ],
}


@app.task
def _get_hosts(parameters):
    """Inspect Fuel CCP setup for hosts and services. Returned dictionary
    has a hostname as a key, and set of services as a value. Example::

        {
            'host-1': [
                {'name': 'nova-conductor'},
                {'name': 'nova-api'},
            ],
            'host-2': [
                {'name': 'nova-compute'},
            ],
        }

    Please note, due to Kubernetes nature some services may change its
    running host in case of failure and following rescheduling. So it
    makes sense to collect data bout hosts and services only before
    running upgrade.
    """
    rv = collections.defaultdict(list)

    # If "kubeconfig" is passed, use it to instantiate Kubernetes client.
    # Otherwise, assume that we run on Kubernetes master where kubectl
    # proxy (no auth) is running for Kubernetes API.
    if 'kubeconfig' in parameters:
        kubeconfig = pykube.KubeConfig.from_file(parameters['kubeconfig'])
    else:
        kubeconfig = pykube.KubeConfig.from_url('http://127.0.0.1:8080')
    kubeapi = pykube.HTTPClient(kubeconfig)

    # Inspect Fuel CCP pods and create appropriate model for Kostyor.
    #
    # It's important to note that we can't use ".ccp.yaml" alone as it
    # doesn't provide enough information. E.g., nodes may be specified
    # using "regexp" which means assign specified services on Kubernetes
    # nodes that match the regexp. Even if manage to resolve those regexps
    # into Kubernetes nodes, the things go worse since CCP supports
    # replicas number and it might be lesser than resolved nodes.
    #
    # So it seems like the only simple and closer-to-reality solution is
    # to iterate over Kubernetes pods and create deployment model based
    # on them. It won't work in case some pod is rescheduled onto other
    # node (failover case), but we have what we have.
    pods = pykube.Pod.objects(kubeapi)\
        .filter(namespace=parameters.get('kubenamespace', 'ccp'))

    for pod in pods:
        ccpapp = pod.labels.get('app')

        if ccpapp in _SERVICES_BY_CCPAPP:
            rv[pod.obj['spec']['nodeName']].extend(
                {
                    'name': service,
                }
                for service in _SERVICES_BY_CCPAPP[ccpapp]
            )

    return rv


class Driver(ServiceDiscovery):

    def __init__(self, **parameters):
        #: Supported keys:
        #:
        #: kubeconfig (default: kubeproxy localhost endpoint)
        #:   A path to kubectl configuration file.
        #:
        #: kubenamespace (default: ccp)
        #:   Kubernetes namespace to be used to collect running PODs from.
        #:
        self._parameters = parameters

    def discover(self):
        return {
            'hosts': _get_hosts.delay(self._parameters).get(),
        }
