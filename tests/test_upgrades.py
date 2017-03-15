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

import os
import sys
import tempfile

import mock
import pytest

from kostyor.rpc import app
from kostyor_fuelccp import upgrades

from .common import set_conf, get_conf, get_hosts, get_fixture


class TestSetAppVersion(object):

    @pytest.fixture
    def tmpfile(self):
        fd, path = tempfile.mkstemp()
        os.close(fd)
        yield path
        os.remove(path)

    def test_app_image_is_inserted(self, tmpfile):
        set_conf(tmpfile, {
            'registry': {
                'address': '127.0.0.1:31500'
            },
            'images': {
                'namespace': 'openstack/mitaka',
            }})

        upgrades._set_app_version(['keystone'], {
            'ccpconfig': tmpfile,
            'image': {
                'namespace': 'openstack/newton',
            }
        })

        assert get_conf(tmpfile) == {
            'registry': {
                'address': '127.0.0.1:31500',
            },
            'images': {
                'namespace': 'openstack/mitaka',
                'image_specs': {
                    'upgrade-keystone': {
                        'namespace': 'openstack/newton',
                    },
                    'keystone': {
                        'namespace': 'openstack/newton',
                    },
                },
            },
        }

    def test_multi_app_image_is_inserted(self, tmpfile):
        set_conf(tmpfile, {
            'registry': {
                'address': '127.0.0.1:31500'
            },
            'images': {
                'namespace': 'openstack/mitaka',
            }})

        upgrades._set_app_version(['keystone', 'nova-api'], {
            'ccpconfig': tmpfile,
            'image': {
                'namespace': 'openstack/newton',
            }
        })

        assert get_conf(tmpfile) == {
            'registry': {
                'address': '127.0.0.1:31500',
            },
            'images': {
                'namespace': 'openstack/mitaka',
                'image_specs': {
                    'upgrade-keystone': {
                        'namespace': 'openstack/newton',
                    },
                    'keystone': {
                        'namespace': 'openstack/newton',
                    },
                    'nova-api': {
                        'namespace': 'openstack/newton',
                    },
                    'nova-upgrade': {
                        'namespace': 'openstack/newton',
                    },
                },
            },
        }

    def test_app_image_is_overridden(self, tmpfile):
        set_conf(tmpfile, {
            'registry': {
                'address': '127.0.0.1:31500',
            },
            'images': {
                'namespace': 'openstack/mitaka',
                'image_specs': {
                    'keystone': {
                        'namespace': 'openstack/mitaka',
                    },
                },
            }
        })

        upgrades._set_app_version(['keystone'], {
            'ccpconfig': tmpfile,
            'image': {
                'namespace': 'openstack/newton',
            }
        })

        assert get_conf(tmpfile) == {
            'registry': {
                'address': '127.0.0.1:31500',
            },
            'images': {
                'namespace': 'openstack/mitaka',
                'image_specs': {
                    'upgrade-keystone': {
                        'namespace': 'openstack/newton',
                    },
                    'keystone': {
                        'namespace': 'openstack/newton',
                    },
                },
            },
        }

    def test_app_image_does_not_reset_others(self, tmpfile):
        set_conf(tmpfile, {
            'registry': {
                'address': '127.0.0.1:31500',
            },
            'images': {
                'namespace': 'openstack/mitaka',
                'image_specs': {
                    'keystone': {
                        'namespace': 'openstack/mitaka',
                    },
                },
            }
        })

        upgrades._set_app_version(['nova-api'], {
            'ccpconfig': tmpfile,
            'image': {
                'namespace': 'openstack/newton',
            }
        })

        assert get_conf(tmpfile) == {
            'registry': {
                'address': '127.0.0.1:31500',
            },
            'images': {
                'namespace': 'openstack/mitaka',
                'image_specs': {
                    'keystone': {
                        'namespace': 'openstack/mitaka',
                    },
                    'nova-upgrade': {
                        'namespace': 'openstack/newton',
                    },
                    'nova-api': {
                        'namespace': 'openstack/newton',
                    },
                },
            },
        }


class TestWaitAppVersion(object):

    @pytest.fixture(autouse=True)
    def use_fake_time_sleep(self, monkeypatch):
        self.sleep = mock.Mock()
        monkeypatch.setattr('kostyor_fuelccp.upgrades.time.sleep', self.sleep)

    @pytest.fixture(autouse=True)
    def use_fake_response(self, monkeypatch):
        self.response = mock.Mock()
        self.api = mock.Mock(return_value=mock.Mock(json=self.response))

        monkeypatch.setattr(
            'kostyor_fuelccp.upgrades.pykube.HTTPClient.get', self.api)

    def test_everything_ready(self):
        self.response.return_value = \
            get_fixture(os.path.join('pods', 'nova-api_ready.json'))

        upgrades._wait_app_version(
            ['nova-api'],
            {
                'image': {
                    'namespace': 'mirantis/ccp/stable/newton',
                }
            }
        )
        assert self.api.call_count == 1
        assert self.sleep.call_count == 0

    def test_retry_on_old_container(self):
        self.response.side_effect = [
            get_fixture(os.path.join('pods', 'nova-api_not-ready.json')),
            get_fixture(os.path.join('pods', 'nova-api_not-ready.json')),
            get_fixture(os.path.join('pods', 'nova-api_ready.json')),
        ]

        upgrades._wait_app_version(
            ['nova-api'],
            {
                'image': {
                    'namespace': 'mirantis/ccp/stable/newton',
                }
            }
        )
        assert self.api.call_count == 3
        assert self.sleep.call_count == 2

    def test_component_is_ready(self):
        self.response.return_value = \
            get_fixture(os.path.join('pods', 'nova_ready.json'))

        upgrades._wait_app_version(
            [
                'nova-api',
                'nova-compute',
                'nova-compute-ironic',
                'nova-conductor',
                'nova-consoleauth',
                'nova-novncproxy',
                'nova-scheduler',
            ],
            {
                'image': {
                    'namespace': 'mirantis/ccp/stable/newton',
                }
            }
        )
        assert self.api.call_count == 1
        assert self.sleep.call_count == 0


class TestDriver(object):

    @pytest.fixture(autouse=True)
    def use_sync_tasks(self, monkeypatch):
        monkeypatch.setattr(app.app.conf, 'CELERY_ALWAYS_EAGER', True)

    @pytest.fixture(autouse=True)
    def use_fake_popen(self, monkeypatch):
        self.popen = mock.Mock()
        self.popen.return_value.returncode = 0

        monkeypatch.setattr(
            sys.modules['kostyor.rpc.tasks.execute'].subprocess,
            'Popen',
            self.popen
        )

    @pytest.fixture(autouse=True)
    def use_fake_set_app_version(self, monkeypatch):
        self.set_app_version = mock.Mock()
        monkeypatch.setattr(
            'kostyor_fuelccp.upgrades._set_app_version',
            self.set_app_version
        )

    @pytest.fixture(autouse=True)
    def use_fake_wait_app_version(self, monkeypatch):
        self.wait_app_version = mock.Mock()
        monkeypatch.setattr(
            'kostyor_fuelccp.upgrades._wait_app_version',
            self.wait_app_version
        )

    def setup(self):
        self.driver = upgrades.Driver()

    def test_start(self):
        self.driver.start({'name': 'nova-compute'}, get_hosts('compute1'))()

        self.set_app_version.assert_called_once_with(
            [
                'nova-api',
                'nova-compute',
                'nova-compute-ironic',
                'nova-conductor',
                'nova-consoleauth',
                'nova-novncproxy',
                'nova-scheduler',
            ],
            {
                'ccpconfig': os.path.expanduser('~/.ccp.yaml'),
                'image': {
                    'namespace': 'mirantis/ccp/stable/newton'
                }
            }
        )
        self.popen.assert_called_once_with(
            [
                'ccp', 'deploy',
            ],
            cwd=None
        )
        self.wait_app_version.assert_called_once_with(
            [
                'nova-api',
                'nova-compute',
                'nova-compute-ironic',
                'nova-conductor',
                'nova-consoleauth',
                'nova-novncproxy',
                'nova-scheduler',
            ],
            {
                'ccpconfig': os.path.expanduser('~/.ccp.yaml'),
                'image': {
                    'namespace': 'mirantis/ccp/stable/newton'
                }
            }
        )
