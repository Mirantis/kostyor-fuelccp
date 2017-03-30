import os

from io import open
from setuptools import setup, find_packages


here = os.path.dirname(__file__)

with open(os.path.join(here, 'README.rst'), 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='kostyor-fuelccp',
    description='Fuel CCP driver for Kostyor',
    long_description=long_description,
    license='Apache 2.0',
    url='http://github.com/Mirantis/kostyor-fuelccp/',
    keywords='openstack kostyor driver fuel-ccp upgrade day2 ops',
    author='Mirantis ERE',
    author_email='mos-ere@mirantis.com',
    packages=find_packages(exclude=['docs', 'tests*']),
    include_package_data=True,
    zip_safe=False,
    use_scm_version=True,
    python_requires='>=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*',
    setup_requires=[
        'setuptools_scm >= 1.15',
    ],
    install_requires=[
        'pykube >= 0.14',
        'PyYAML >= 3.12',
    ],
    entry_points={
        'kostyor.discovery_drivers': [
            'fuel-ccp = kostyor_fuelccp.discover:Driver',
        ],
        'kostyor.upgrades.drivers': [
            'fuel-ccp = kostyor_fuelccp.upgrades:Driver',
        ],
    },
    classifiers=[
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python',
        'Topic :: System :: Installation/Setup',
        'Topic :: System :: Systems Administration',
    ],
)
