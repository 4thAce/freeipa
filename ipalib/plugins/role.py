# Authors:
#   Rob Crittenden <rcritten@redhat.com>
#   Pavel Zuna <pzuna@redhat.com>
#
# Copyright (C) 2009  Red Hat
# see file 'COPYING' for use and warranty information
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Roles

A role is used for fine-grained delegation. A permission grants the ability
to perform given low-level tasks (add a user, modify a group, etc.). A
privilege combines one or more permissions into a higher-level abstraction
such as useradmin. A useradmin would be able to add, delete and modify users.

Privileges are assigned to Roles.

Users, groups, hosts and hostgroups may be members of a Role.

Roles can not contain other roles.

EXAMPLES:

 Add a new role:
   ipa role-add --desc="Junior-level admin" junioradmin

 Add some privileges to this role:
   ipa role-add-privilege --privileges=addusers junioradmin
   ipa role-add-privilege --privileges=change_password junioradmin
   ipa role-add-privilege --privileges=add_user_to_default_group juioradmin

 Add a group of users to this role:
   ipa group-add --desc="User admins" useradmins
   ipa role-add-member --groups=useradmins junioradmin

 Display information about a role:
   ipa role-show junioradmin

 The result of this is that any users in the group 'useradmins' can
 add users, reset passwords or add a user to the default IPA user group.
"""

from ipalib.plugins.baseldap import *
from ipalib import api, Str, _, ngettext
from ipalib import Command
from ipalib.plugins import privilege


class role(LDAPObject):
    """
    Role object.
    """
    container_dn = api.env.container_rolegroup
    object_name = 'role'
    object_name_plural = 'roles'
    object_class = ['groupofnames', 'nestedgroup']
    default_attributes = ['cn', 'description', 'member', 'memberof',
        'memberindirect'
    ]
    attribute_members = {
        'member': ['user', 'group', 'host', 'hostgroup'],
        'memberof': ['privilege'],
#        'memberindirect': ['user', 'group', 'host', 'hostgroup'],
    }
    reverse_members = {
        'member': ['privilege'],
    }
    rdnattr='cn'

    label = _('Role')

    takes_params = (
        Str('cn',
            cli_name='name',
            label=_('Role name'),
            primary_key=True,
            normalizer=lambda value: value.lower(),
        ),
        Str('description',
            cli_name='desc',
            label=_('Description'),
            doc=_('A description of this role-group'),
        ),
    )

api.register(role)


class role_add(LDAPCreate):
    """
    Add a new role.
    """

    msg_summary = _('Added role "%(value)s"')

api.register(role_add)


class role_del(LDAPDelete):
    """
    Delete a role.
    """

    msg_summary = _('Deleted role "%(value)s"')

api.register(role_del)


class role_mod(LDAPUpdate):
    """
    Modify a role.
    """

    msg_summary = _('Modified role "%(value)s"')

api.register(role_mod)


class role_find(LDAPSearch):
    """
    Search for roles.
    """

    msg_summary = ngettext(
        '%(count)d role matched', '%(count)d roles matched'
    )

api.register(role_find)


class role_show(LDAPRetrieve):
    """
    Display information about a role.
    """

api.register(role_show)


class role_add_member(LDAPAddMember):
    """
    Add members to a role.
    """

api.register(role_add_member)


class role_remove_member(LDAPRemoveMember):
    """
    Remove members from a role.
    """

api.register(role_remove_member)


class role_add_privilege(LDAPAddReverseMember):
    """
    Add privileges to a role.
    """
    show_command = 'role_show'
    member_command = 'privilege_add_member'
    reverse_attr = 'privilege'
    member_attr = 'role'

    has_output = (
        output.Entry('result'),
        output.Output('failed',
            type=dict,
            doc=_('Members that could not be added'),
        ),
        output.Output('completed',
            type=int,
            doc=_('Number of privileges added'),
        ),
    )

api.register(role_add_privilege)


class role_remove_privilege(LDAPRemoveReverseMember):
    """
    Remove privileges from a role.
    """
    show_command = 'role_show'
    member_command = 'privilege_remove_member'
    reverse_attr = 'privilege'
    member_attr = 'role'

    has_output = (
        output.Entry('result'),
        output.Output('failed',
            type=dict,
            doc=_('Members that could not be added'),
        ),
        output.Output('completed',
            type=int,
            doc=_('Number of privileges removed'),
        ),
    )

api.register(role_remove_privilege)