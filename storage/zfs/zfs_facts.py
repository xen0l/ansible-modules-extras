#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2016, Adam Števko <adam.stevko@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible. If not, see <http://www.gnu.org/licenses/>.
#

DOCUMENTATION = '''
---
module: zfs_facts
short_description: Gather facts about ZFS datasets.
description:
  - Gather facts from ZFS dataset properties. 
version_added: "2.3"
author: Adam Števko (@xen0l)
options:
    name:
        description:
            - ZFS dataset name.
        alias: [ "ds", "dataset" ]
        type: str
        required: yes
    recurse:
        description:
            - Specifies if properties for any children should be recursively
              display.
        type: bool
        default: False
        required: false
    parsable:
        description:
            - Specifies if property values should be displayed in machine
              friendly format.
        type: bool
        default: False
        required: false
    properties:
        description:
            - Specifies which dataset properties should be queried in comma-separated format.
              For more information about dataset properties, check zfs(1M) man page.
        alias: [ "props" ]
        type: str
        default: all
        required: false
    type:
        description:
            - Specifies which datasets types to display. Multiple values have to be
              provided in comma-separated form.
        alias: [ "props" ]
        type: str
        default: all
        choices: [ 'all', 'filesystem', 'volume', 'snapshot', 'bookmark' ]
        required: false
    depth:
        description:
            - Specifiies recurion depth.
        type: int
        default: None
        required: false
'''

EXAMPLES = '''
# Gather facts about ZFS dataset rpool/export/home
zfs_facts: dataset=rpool/export/home

# Report space usage on ZFS filesystems under data/home
zfs_facts: name=data/home recurse=yes type=filesystem
debug: msg='ZFS dataset {{ item.name }} consumes {{ item.used }} of disk space.'
with_items: '{{ ansible_zfs_datasets }}
'''

RETURN = '''
'''

import os
from collections import defaultdict


SUPPORTED_TYPES = ['all', 'filesystem', 'volume', 'snapshot', 'bookmark']


class ZFSFacts(object):
    def __init__(self, module):

        self.module = module

        self.name = module.params['name']
        self.recurse = module.params['recurse']
        self.parsable = module.params['parsable']
        self.properties = module.params['properties']
        self.type = module.params['type']
        self.depth = module.params['depth']

        self._datasets = defaultdict(dict)
        self.facts = []

    def dataset_exists(self):
        cmd = [self.module.get_bin_path('zfs')]

        cmd.append('list')
        cmd.append(self.name)

        (rc, out, err) = self.module.run_command(cmd)

        if rc == 0:
            return True
        else:
            return False

    def get_facts(self):
        cmd = [self.module.get_bin_path('zfs')]

        cmd.append('get')
        cmd.append('-H')
        if self.parsable:
            cmd.append('-p')
        if self.recurse:
            cmd.append('-r')
        if int(self.depth) != 0:
            cmd.append('-d')
            cmd.append('%s' % self.depth)
        if self.type:
            cmd.append('-t')
            cmd.append(self.type)
        cmd.append('-o')
        cmd.append('name,property,value')
        cmd.append(self.properties)
        cmd.append(self.name)

        (rc, out, err) = self.module.run_command(cmd)

        if rc == 0:
            for line in out.splitlines():
                dataset, property, value = line.split('\t')

                self._datasets[dataset].update({property: value})

            for k, v in self._datasets.iteritems():
                v.update({'name': k})
                self.facts.append(v)

            return {'ansible_zfs_datasets': self.facts}
        else:
            self.module.fail_json(msg='Error while trying to get facts about ZFS dataset: %s' % self.name,
                                  stderr=err,
                                  rc=rc)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(required=True, aliases=['ds', 'dataset'], type='str'),
            recurse=dict(required=False, default=False, type='bool'),
            parsable=dict(required=False, default=False, type='bool'),
            properties=dict(required=False, default='all', type='str'),
            type=dict(required=False, default='all', type='str', choices=SUPPORTED_TYPES),
            depth=dict(required=False, default=0, type='int')
        ),
        supports_check_mode=True
    )

    zfs_facts = ZFSFacts(module)

    result = {}
    result['changed'] = False
    result['name'] = zfs_facts.name

    if zfs_facts.parsable:
        result['parsable'] = zfs_facts.parsable

    if zfs_facts.recurse:
        result['recurse'] = zfs_facts.recurse

    if zfs_facts.dataset_exists():
        result['ansible_facts'] = zfs_facts.get_facts()
    else:
        module.fail_json(msg='ZFS dataset %s does not exist!' % zfs_facts.name)

    module.exit_json(**result)


from ansible.module_utils.basic import *
if __name__ == '__main__':
    main()
