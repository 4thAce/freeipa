# Authors:
#   Jr Aquino <jr.aquino@citrixonline.com>
#
# Copyright (C) 2010  Red Hat
# see file 'COPYING' for use and warranty information
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; version 2 only
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
"""
Sudo Commands

Commands used as building blocks for sudo

EXAMPLES:

 Create a new commnad
   ipa sudocmd-add --description='For reading log files' /usr/bin/less

 Remove a command
   ipa sudocmd-del /usr/bin/less

"""

import platform
import os
import sys

from ipalib import api, errors, util
from ipalib import Str
from ipalib.plugins.baseldap import *
from ipalib import _, ngettext


class sudocmd(LDAPObject):
    """
    Sudo Command object.
    """
    container_dn = api.env.container_sudocmd
    object_name = 'sudocmd'
    object_name_plural = 'sudocmds'
    object_class = ['ipaobject', 'ipasudocmd']
    # object_class_config = 'ipahostobjectclasses'
    search_attributes = [
        'cn', 'description',
    ]
    default_attributes = [
        'cn', 'description',
    ]
    uuid_attribute = 'ipauniqueid'
    label = _('SudoCmds')

    takes_params = (
        Str('cn',
            cli_name='command',
            label=_('Sudo Command'),
            primary_key=True,
            #normalizer=lambda value: value.lower(),
        ),
        Str('description?',
            cli_name='desc',
            label=_('Description'),
            doc=_('A description of this command'),
        ),
    )

    def get_dn(self, *keys, **options):
        if keys[-1].endswith('.'):
            keys[-1] = keys[-1][:-1]
        dn = super(sudocmd, self).get_dn(*keys, **options)
        try:
            self.backend.get_entry(dn, [''])
        except errors.NotFound:
            try:
                (dn, entry_attrs) = self.backend.find_entry_by_attr(
                    'cn', keys[-1], self.object_class, [''],
                    self.container_dn
                )
            except errors.NotFound:
                pass
        return dn

api.register(sudocmd)

class sudocmd_add(LDAPCreate):
    """
    Create new sudo command.
    """

    msg_summary = _('Added sudo command "%(value)s"')

api.register(sudocmd_add)

class sudocmd_del(LDAPDelete):
    """
    Delete sudo command.
    """

    msg_summary = _('Deleted sudo command "%(value)s"')

api.register(sudocmd_del)

class sudocmd_mod(LDAPUpdate):
    """
    Modify command.
    """

    msg_summary = _('Modified sudo command "%(value)s"')

api.register(sudocmd_mod)

class sudocmd_find(LDAPSearch):
    """
    Search for commands.
    """

    msg_summary = ngettext(
        '%(count)d sudo command matched', '%(count)d sudo command matched'
    )

api.register(sudocmd_find)

class sudocmd_show(LDAPRetrieve):
    """
    Display sudo command.
    """

api.register(sudocmd_show)