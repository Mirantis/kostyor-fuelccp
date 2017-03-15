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

import io
import os
import copy
import time

import pykube
import yaml

from kostyor.rpc import tasks
from kostyor.rpc.app import app
from kostyor.upgrades.drivers import base

from ._misc import get_component_from_service, get_apps_by_component


# Some CCP components define a special target (application) that
# fires additional upgrade jobs, such as database migration and
# so on. It's mandatory to pass them within a component under
# upgrade, as otherwise it's not guarantee to work properly.
_UPGRADE_APPS = {
    'keystone':     'upgrade-keystone',
    'glance':       'upgrade-glance',
    'nova':         'nova-upgrade',
    'neutron':      'upgrade-neutron',
    'heat':         'heat-upgrade',
}


def _is_app_running(pods, app):
    pod = next((pod for pod in pods if pod.labels.get('app') == app), None)
    return bool(pod)


def _is_image_in_use(pods, image, app):
    container = next(
        (
            container
            for pod in pods
            for container in pod.obj['status'].get('containerStatuses', [])
            if container['name'] == app
        ),
        None
    )

    if container:
        container_image, container_image_tag = container['image'].split(':')

        if all([
            # container_image is a string that includes host, namespace
            # and image name; so the only way to compare it with `image`
            # is to check whether namespace is a part of that string.
            image['namespace'] in container_image,
            image.get('tag', 'latest') == container_image_tag,
        ]):
            return True
        return False

    # I have so much hate here and everywhere. :( It's one more hack I have
    # to wrote. Since the driver passes down all services of the component,
    # even those that do not exist in current installation, there's always
    # a chance that container won't be found but we don't want to block
    # the whole procedure. Let's consider if container is not found, then
    # it doesn't exist and so assume it's ready.
    return True


def _set_app_version(apps, parameters):
    with io.open(parameters['ccpconfig'], 'rt', encoding='utf-8') as f:
        conf = yaml.load(f)

    specs = conf.setdefault('images', {}).setdefault('image_specs', {})
    for appname in apps:
        specs[appname] = parameters['image']

        # Do not forget to add a special upgrade app, since otherwise
        # some required actions won't be taken.
        component = get_component_from_service(appname)
        if component in _UPGRADE_APPS:
            specs[_UPGRADE_APPS[component]] = parameters['image']

    with io.open(parameters['ccpconfig'], 'wt', encoding='utf-8') as f:
        yaml.dump(conf, f, default_flow_style=False, encoding=None)


def _wait_app_version(apps, parameters):
    # If "kubeconfig" is passed, use it to instantiate Kubernetes client.
    # Otherwise, assume that we run on Kubernetes master where kubectl
    # proxy (no auth) is running for Kubernetes API.
    if 'kubeconfig' in parameters:
        kubeconfig = pykube.KubeConfig.from_file(parameters['kubeconfig'])
    else:
        kubeconfig = pykube.KubeConfig.from_url('http://127.0.0.1:8080')
    kubeapi = pykube.HTTPClient(kubeconfig)

    # Application is considered successfully deployed when there are only
    # pods with new image and they are in ready state.
    while True:
        pods = pykube.Pod.objects(kubeapi).filter(
            namespace=parameters.get('kubenamespace', 'ccp'),
            selector={'app__in': apps},
        )

        if all([
            # Everything is ready.
            all([
                pod.ready for pod in pods
            ]),
            # At least one application is running.
            #
            # During upgrade of glance, there's a chance that no glance PODs
            # are running (old ones are terminated, new ones - not launched),
            # so we need to ensure that at least one application is running
            # in order to protect us from the premature continuing.
            #
            # It's even more crucial, since 'apps' may contain not deployed
            # services, and not found services are assumed as 'ok' in
            # '_is_image_in_use' check below. In combination with this check,
            # we won't miss the case mentioned in the first paragraph.
            any([
                _is_app_running(pods, app) for app in apps
            ]),
            # Passed applications must use new image.
            all([
                _is_image_in_use(pods, parameters['image'], app)
                for app in apps
            ]),
        ]):
            break

        time.sleep(parameters.get('wait-interval', 10))


@app.task(bind=True, base=tasks.execute.__class__)
def _run_upgrade(self, apps, parameters):
    _set_app_version(apps, parameters)
    super(_run_upgrade.__class__, self).run(
        [
            'ccp', 'deploy',
        ],
        cwd=None,
        ignore_errors=False,
    )
    _wait_app_version(apps, parameters)


class Driver(base.UpgradeDriver):

    def __init__(self, *args, **kwargs):
        super(Driver, self).__init__(*args, **kwargs)

        #: Bunch of parameters that controls upgrades procedure and/or
        #: required to run them properly.
        self._parameters = dict({
            'ccpconfig': os.path.expanduser('~/.ccp.yaml'),
            'image': {
                'namespace': 'mirantis/ccp/stable/newton'
            }
        }, **kwargs)

        #: Due to the fact that we may have one Kubernetes POD that hosts
        #: multiple OpenStack services, we need to ensure that we won't
        #: try to upgrade the same POD multiple times.
        #:
        #: The dict is used to track execution and has the following format:
        #:
        #:   (host, component) -> is-executed
        self._executions = {}

    def start(self, service, hosts):
        # Fuel CCP does not support upgrades by services, only by components.
        # Pity, since it kills Kostyor's value. :/
        component = get_component_from_service(service['name'])
        apps = get_apps_by_component(component)

        # Kostyor's model may contain services we do not support yet. If
        # such one is passed then do nothing. It seems reasonable to ignore
        # and let users to handle them on their own.
        if not apps:
            return tasks.noop.si()

        # Do not upgrade service second time on the same host. This might
        # happened pretty often as OpenStack Ansible playbooks upgrades
        # the whole service at once rather than its separate parts.
        for host in copy.copy(hosts):
            key = host['id'], component
            if self._executions.get(key):
                hosts.remove(host)
            self._executions[key] = True

        if not hosts:
            return tasks.noop.si()

        return _run_upgrade.si(apps, self._parameters)
