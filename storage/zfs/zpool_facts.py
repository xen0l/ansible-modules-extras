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
module: zpool_facts
short_description: Gather facts about ZFS pools.
description
  - Gather facts from ZFS pool properties.
version_added: "2.3"
author: Adam Števko (@xen0l)
options:
    name:
        description:
            - ZFS pool name.
        alias: [ "pool", "zpool" ]
        type: str
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
              For more information about dataset properties, check zpool(1M) man page.
        alias: [ "props" ]
        type: str
        default: all
        required: false
'''

EXAMPLES = '''
# Gather facts about ZFS pool rpool
zpool_facts: pool=rpool

# Gather space usage about all imported ZFS pools
zpool_facts: properties='free,size'
debug: msg='ZFS pool {{ item.name }} has {{ item.free }} free space out of {{ item.size }}.'
with_items: '{{ ansible_zfs_pools }}'
'''

RETURN = '''
'''

import os
from collections import defaultdict


class ZPoolFacts(object):
    def __init__(self, module):

        self.module = module

        self.name = module.params['name']
        self.parsable = module.params['parsable']
        self.properties = module.params['properties']

        self._pools = defaultdict(dict)
        self.facts = []

    def pool_exists(self):
        cmd = [self.module.get_bin_path('zpool')]

        cmd.append('list')
        cmd.append(self.name)

        (rc, out, err) = self.module.run_command(cmd)

        if rc == 0:
            return True
        else:
            return False

    def get_facts(self):
        cmd = [self.module.get_bin_path('zpool')]

        cmd.append('get')
        cmd.append('-H')
        if self.parsable:
            cmd.append('-p')
        cmd.append('-o')
        cmd.append('name,property,value')
        cmd.append(self.properties)
        if self.name:
            cmd.append(self.name)

        (rc, out, err) = self.module.run_command(cmd)

        if rc == 0:
            for line in out.splitlines():
                pool, property, value = line.split('\t')

                self._pools[pool].update({property: value})

            for k, v in self._pools.iteritems():
                v.update({'name': k})
                self.facts.append(v)

            return {'ansible_zfs_pools': self.facts}
        else:
            self.module.fail_json(msg='Error while trying to get facts about ZFS pool: %s' % self.name,
                                  stderr=err,
                                  rc=rc)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(required=False, aliases=['pool', 'zpool'], type='str'),
            parsable=dict(required=False, default=False, type='bool'),
            properties=dict(required=False, default='all', type='str'),
        ),
        supports_check_mode=True
    )

    zpool_facts = ZPoolFacts(module)

    result = {}
    result['changed'] = False
    result['name'] = zpool_facts.name

    if zpool_facts.parsable:
        result['parsable'] = zpool_facts.parsable

    if zpool_facts.name is not None:
        if zpool_facts.pool_exists():
            result['ansible_facts'] = zpool_facts.get_facts()
        else:
            module.fail_json(msg='ZFS pool %s does not exist!' % zpool_facts.name)
    else:
        result['ansible_facts'] = zpool_facts.get_facts()

    module.exit_json(**result)


from ansible.module_utils.basic import *
if __name__ == '__main__':
    main()
