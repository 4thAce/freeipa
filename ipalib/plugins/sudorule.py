# Authors:
#   Jr Aquino <jr.aquino@citrixonline.com>
#
# Copyright (C) 2010  Red Hat
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

from ipalib import api, errors
from ipalib import Str, StrEnum
from ipalib.plugins.baseldap import *
from ipalib import _, ngettext

__doc__ = _("""
Sudo Rules

Sudo (su "do") allows a system administrator to delegate authority to
give certain users (or groups of users) the ability to run some (or all)
commands as root or another user while providing an audit trail of the
commands and their arguments.

FreeIPA provides a means to configure the various aspects of Sudo:
   Users: The user(s)/group(s) allowed to envoke Sudo.
   Hosts: The host(s)/hostgroup(s) which the user is allowed to to invoke Sudo.
   Allow Command: The specific command(s) permited to be run via Sudo.
   Deny Command: The specific command(s) prohibited to be run via Sudo.
   RunAsUser: The user(s) or group(s) of users whose rights Sudo will be invoked with.
   RunAsGroup: The group(s) whose gid rights Sudo will be invoked with.
   Options: The various Sudoers Options that can modify Sudo's behavior.

FreeIPA provides a designated binddn to use with Sudo located at:
uid=sudo,cn=sysaccounts,cn=etc,dc=example,dc=com

To enable the binddn run the following command to set the password:
LDAPTLS_CACERT=/etc/ipa/ca.crt /usr/bin/ldappasswd -S -W \
-h ipa.example.com -ZZ -D "cn=Directory Manager" \
uid=sudo,cn=sysaccounts,cn=etc,dc=example,dc=com

For more information, see the FreeIPA Documentation to Sudo.
""")

topic = ('sudo', _('Commands for controlling sudo configuration'))

def deprecated(attribute):
    raise errors.ValidationError(name=attribute, error=_('this option has been deprecated.'))

def validate_externaluser(ugettext, value):
    deprecated('externaluser')

def validate_runasextuser(ugettext, value):
    deprecated('runasexternaluser')

def validate_runasextgroup(ugettext, value):
    deprecated('runasexternalgroup')

class sudorule(LDAPObject):
    """
    Sudo Rule object.
    """
    container_dn = api.env.container_sudorule
    object_name = _('sudo rule')
    object_name_plural = _('sudo rules')
    object_class = ['ipaassociation', 'ipasudorule']
    default_attributes = [
        'cn', 'ipaenabledflag',
        'description', 'usercategory', 'hostcategory',
        'cmdcategory', 'memberuser', 'memberhost',
        'memberallowcmd', 'memberdenycmd', 'ipasudoopt',
    ]
    uuid_attribute = 'ipauniqueid'
    rdn_attribute = 'ipauniqueid'
    attribute_members = {
        'memberuser': ['user', 'group'],
        'memberhost': ['host', 'hostgroup'],
        'memberallowcmd': ['sudocmd', 'sudocmdgroup'],
        'memberdenycmd': ['sudocmd', 'sudocmdgroup'],
        'ipasudorunas': ['user', 'group'],
        'ipasudorunasgroup': ['group'],
    }

    label = _('Sudo Rules')
    label_singular = _('Sudo Rule')

    takes_params = (
        Str('cn',
            cli_name='sudorule_name',
            label=_('Rule name'),
            primary_key=True,
        ),
        Str('description?',
            cli_name='desc',
            label=_('Description'),
        ),
        Flag('ipaenabledflag?',
             label=_('Enabled'),
             flags=['no_create', 'no_update', 'no_search'],
        ),
        StrEnum('usercategory?',
            cli_name='usercat',
            label=_('User category'),
            doc=_('User category the rule applies to'),
            values=(u'all', ),
        ),
        StrEnum('hostcategory?',
            cli_name='hostcat',
            label=_('Host category'),
            doc=_('Host category the rule applies to'),
            values=(u'all', ),
        ),
        StrEnum('cmdcategory?',
            cli_name='cmdcat',
            label=_('Command category'),
            doc=_('Command category the rule applies to'),
            values=(u'all', ),
        ),
        StrEnum('ipasudorunasusercategory?',
            cli_name='runasusercat',
            label=_('RunAs User category'),
            doc=_('RunAs User category the rule applies to'),
            values=(u'all', ),
        ),
        StrEnum('ipasudorunasgroupcategory?',
            cli_name='runasgroupcat',
            label=_('RunAs Group category'),
            doc=_('RunAs Group category the rule applies to'),
            values=(u'all', ),
        ),
        Str('memberuser_user?',
            label=_('Users'),
            flags=['no_create', 'no_update', 'no_search'],
        ),
        Str('memberuser_group?',
            label=_('User Groups'),
            flags=['no_create', 'no_update', 'no_search'],
        ),
        Str('memberhost_host?',
            label=_('Hosts'),
            flags=['no_create', 'no_update', 'no_search'],
        ),
        Str('memberhost_hostgroup?',
            label=_('Host Groups'),
            flags=['no_create', 'no_update', 'no_search'],
        ),
        Str('memberallowcmd_sudocmd?',
            label=_('Sudo Allow Commands'),
            flags=['no_create', 'no_update', 'no_search'],
        ),
        Str('memberdenycmd_sudocmd?',
            label=_('Sudo Deny Commands'),
            flags=['no_create', 'no_update', 'no_search'],
        ),
        Str('memberallowcmd_sudocmdgroup?',
            label=_('Sudo Allow Command Groups'),
            flags=['no_create', 'no_update', 'no_search'],
        ),
        Str('memberdenycmd_sudocmdgroup?',
            label=_('Sudo Deny Command Groups'),
            flags=['no_create', 'no_update', 'no_search'],
        ),
        Str('ipasudorunas_user?',
            label=_('RunAs Users'),
            doc=_('Run as a user'),
            flags=['no_create', 'no_update', 'no_search'],
        ),
        Str('ipasudorunas_group?',
            label=_('Groups of RunAs Users'),
            doc=_('Run as any user within a specified group'),
            flags=['no_create', 'no_update', 'no_search'],
        ),
        Str('externaluser?', validate_externaluser,
            cli_name='externaluser',
            label=_('External User'),
            doc=_('External User the rule applies to (sudorule-find only)'),
        ),
        Str('ipasudorunasextuser?', validate_runasextuser,
            cli_name='runasexternaluser',
            label=_('RunAs External User'),
            doc=_('External User the commands can run as (sudorule-find only)'),
        ),
        Str('ipasudorunasextgroup?', validate_runasextgroup,
            cli_name='runasexternalgroup',
            label=_('RunAs External Group'),
            doc=_('External Group the commands can run as (sudorule-find only)'),
        ),
        Str('ipasudoopt?',
            label=_('Sudo Option'),
            flags=['no_create', 'no_update', 'no_search'],
        ),
        Str('ipasudorunasgroup_group?',
            label=_('RunAs Groups'),
            doc=_('Run with the gid of a specified POSIX group'),
            flags=['no_create', 'no_update', 'no_search'],
        ),
    )

api.register(sudorule)


class sudorule_add(LDAPCreate):
    __doc__ = _('Create new Sudo Rule.')

    def pre_callback(self, ldap, dn, entry_attrs, attrs_list, *keys, **options):
        # Sudo Rules are enabled by default
        entry_attrs['ipaenabledflag'] = 'TRUE'
        return dn

    msg_summary = _('Added Sudo Rule "%(value)s"')

api.register(sudorule_add)


class sudorule_del(LDAPDelete):
    __doc__ = _('Delete Sudo Rule.')

    msg_summary = _('Deleted Sudo Rule "%(value)s"')

api.register(sudorule_del)


class sudorule_mod(LDAPUpdate):
    __doc__ = _('Modify Sudo Rule.')

    msg_summary = _('Modified Sudo Rule "%(value)s"')

api.register(sudorule_mod)


class sudorule_find(LDAPSearch):
    __doc__ = _('Search for Sudo Rule.')

    msg_summary = ngettext(
        '%(count)d Sudo Rule matched', '%(count)d Sudo Rules matched', 0
    )

api.register(sudorule_find)


class sudorule_show(LDAPRetrieve):
    __doc__ = _('Display Sudo Rule.')

api.register(sudorule_show)


class sudorule_enable(LDAPQuery):
    __doc__ = _('Enable a Sudo Rule.')

    def execute(self, cn):
        ldap = self.obj.backend

        dn = self.obj.get_dn(cn)
        entry_attrs = {'ipaenabledflag': 'TRUE'}

        try:
            ldap.update_entry(dn, entry_attrs)
        except errors.EmptyModlist:
            pass
        except errors.NotFound:
            self.obj.handle_not_found(cn)

        return dict(result=True)

    def output_for_cli(self, textui, result, cn):
        textui.print_dashed(_('Enabled Sudo Rule "%s"') % cn)

api.register(sudorule_enable)


class sudorule_disable(LDAPQuery):
    __doc__ = _('Disable a Sudo Rule.')

    def execute(self, cn):
        ldap = self.obj.backend

        dn = self.obj.get_dn(cn)
        entry_attrs = {'ipaenabledflag': 'FALSE'}

        try:
            ldap.update_entry(dn, entry_attrs)
        except errors.EmptyModlist:
            pass
        except errors.NotFound:
            self.obj.handle_not_found(cn)

        return dict(result=True)

    def output_for_cli(self, textui, result, cn):
        textui.print_dashed(_('Disabled Sudo Rule "%s"') % cn)

api.register(sudorule_disable)


class sudorule_add_allow_command(LDAPAddMember):
    __doc__ = _('Add commands and sudo command groups affected by Sudo Rule.')

    member_attributes = ['memberallowcmd']
    member_count_out = ('%i object added.', '%i objects added.')

api.register(sudorule_add_allow_command)


class sudorule_remove_allow_command(LDAPRemoveMember):
    __doc__ = _('Remove commands and sudo command groups affected by Sudo Rule.')

    member_attributes = ['memberallowcmd']
    member_count_out = ('%i object removed.', '%i objects removed.')

api.register(sudorule_remove_allow_command)


class sudorule_add_deny_command(LDAPAddMember):
    __doc__ = _('Add commands and sudo command groups affected by Sudo Rule.')

    member_attributes = ['memberdenycmd']
    member_count_out = ('%i object added.', '%i objects added.')

api.register(sudorule_add_deny_command)


class sudorule_remove_deny_command(LDAPRemoveMember):
    __doc__ = _('Remove commands and sudo command groups affected by Sudo Rule.')

    member_attributes = ['memberdenycmd']
    member_count_out = ('%i object removed.', '%i objects removed.')

api.register(sudorule_remove_deny_command)


class sudorule_add_user(LDAPAddMember):
    __doc__ = _('Add users and groups affected by Sudo Rule.')

    member_attributes = ['memberuser']
    member_count_out = ('%i object added.', '%i objects added.')

    def post_callback(self, ldap, completed, failed, dn, entry_attrs, *keys, **options):
        completed_external = 0
        # Sift through the user failures. We assume that these are all
        # users that aren't stored in IPA, aka external users.
        if 'memberuser' in failed and 'user' in failed['memberuser']:
            (dn, entry_attrs_) = ldap.get_entry(dn, ['externaluser'])
            members = entry_attrs.get('memberuser', [])
            external_users = entry_attrs_.get('externaluser', [])
            failed_users = []
            for user in failed['memberuser']['user']:
                username = user[0].lower()
                user_dn = self.api.Object['user'].get_dn(username)
                if username not in external_users and user_dn not in members:
                    external_users.append(username)
                    completed_external += 1
                else:
                    failed_users.append(username)
            if completed_external:
                try:
                    ldap.update_entry(dn, {'externaluser': external_users})
                except errors.EmptyModlist:
                    pass
                failed['memberuser']['user'] = failed_users
                entry_attrs['externaluser'] = external_users
        return (completed + completed_external, dn)

api.register(sudorule_add_user)


class sudorule_remove_user(LDAPRemoveMember):
    __doc__ = _('Remove users and groups affected by Sudo Rule.')

    member_attributes = ['memberuser']
    member_count_out = ('%i object removed.', '%i objects removed.')

    def post_callback(self, ldap, completed, failed, dn, entry_attrs, *keys, **options):
        # Run through the user failures and gracefully remove any defined as
        # as an externaluser.
        if 'memberuser' in failed and 'user' in failed['memberuser']:
            (dn, entry_attrs_) = ldap.get_entry(dn, ['externaluser'])
            external_users = entry_attrs_.get('externaluser', [])
            failed_users = []
            completed_external = 0
            for user in failed['memberuser']['user']:
                username = user[0].lower()
                if username in external_users:
                    external_users.remove(username)
                    completed_external += 1
                else:
                    failed_users.append(username)
            if completed_external:
                try:
                    ldap.update_entry(dn, {'externaluser': external_users})
                except errors.EmptyModlist:
                    pass
                failed['memberuser']['user'] = failed_users
                entry_attrs['externaluser'] = external_users
        return (completed + completed_external, dn)

api.register(sudorule_remove_user)


class sudorule_add_host(LDAPAddMember):
    __doc__ = _('Add hosts and hostgroups affected by Sudo Rule.')

    member_attributes = ['memberhost']
    member_count_out = ('%i object added.', '%i objects added.')

    def post_callback(self, ldap, completed, failed, dn, entry_attrs, *keys, **options):
        completed_external = 0
        # Sift through the host failures. We assume that these are all
        # hosts that aren't stored in IPA, aka external hosts.
        if 'memberhost' in failed and 'host' in failed['memberhost']:
            (dn, entry_attrs_) = ldap.get_entry(dn, ['externalhost'])
            members = entry_attrs.get('memberhost', [])
            external_hosts = entry_attrs_.get('externalhost', [])
            failed_hosts = []
            for host in failed['memberhost']['host']:
                hostname = host[0].lower()
                host_dn = self.api.Object['host'].get_dn(hostname)
                if hostname not in external_hosts and host_dn not in members:
                    external_hosts.append(hostname)
                    completed_external += 1
                else:
                    failed_hosts.append(hostname)
            if completed_external:
                try:
                    ldap.update_entry(dn, {'externalhost': external_hosts})
                except errors.EmptyModlist:
                    pass
                failed['memberhost']['host'] = failed_hosts
                entry_attrs['externalhost'] = external_hosts
        return (completed + completed_external, dn)

api.register(sudorule_add_host)


class sudorule_remove_host(LDAPRemoveMember):
    __doc__ = _('Remove hosts and hostgroups affected by Sudo Rule.')

    member_attributes = ['memberhost']
    member_count_out = ('%i object removed.', '%i objects removed.')

    def post_callback(self, ldap, completed, failed, dn, entry_attrs, *keys, **options):
        # Run through the host failures and gracefully remove any defined as
        # as an externalhost.
        if 'memberhost' in failed and 'host' in failed['memberhost']:
            (dn, entry_attrs_) = ldap.get_entry(dn, ['externalhost'])
            external_hosts = entry_attrs_.get('externalhost', [])
            failed_hosts = []
            completed_external = 0
            for host in failed['memberhost']['host']:
                hostname = host[0].lower()
                if hostname in external_hosts:
                    external_hosts.remove(hostname)
                    completed_external += 1
                else:
                    failed_hosts.append(hostname)
            if completed_external:
                try:
                    ldap.update_entry(dn, {'externalhost': external_hosts})
                except errors.EmptyModlist:
                    pass
                failed['memberhost']['host'] = failed_hosts
                if external_hosts:
                    entry_attrs['externalhost'] = external_hosts
        return (completed + completed_external, dn)

api.register(sudorule_remove_host)


class sudorule_add_runasuser(LDAPAddMember):
    __doc__ = _('Add users and groups for Sudo to execute as.')

    member_attributes = ['ipasudorunas']
    member_count_out = ('%i object added.', '%i objects added.')

    def post_callback(self, ldap, completed, failed, dn, entry_attrs, *keys, **options):
        completed_external = 0
        # Sift through the user failures. We assume that these are all
        # users that aren't stored in IPA, aka external users.
        if 'ipasudorunas' in failed and 'user' in failed['ipasudorunas']:
            (dn, entry_attrs_) = ldap.get_entry(dn, ['ipasudorunasextuser'])
            members = entry_attrs.get('ipasudorunas', [])
            external_users = entry_attrs_.get('ipasudorunasextuser', [])
            failed_users = []
            for user in failed['ipasudorunas']['user']:
                username = user[0].lower()
                user_dn = self.api.Object['user'].get_dn(username)
                if username not in external_users and user_dn not in members:
                    external_users.append(username)
                    completed_external += 1
                else:
                    failed_users.append(username)
            if completed_external:
                try:
                    ldap.update_entry(dn, {'ipasudorunasextuser': external_users})
                except errors.EmptyModlist:
                    pass
                failed['ipasudorunas']['user'] = failed_users
                entry_attrs['ipasudorunasextuser'] = external_users
        return (completed + completed_external, dn)

api.register(sudorule_add_runasuser)


class sudorule_remove_runasuser(LDAPRemoveMember):
    __doc__ = _('Remove users and groups for Sudo to execute as.')

    member_attributes = ['ipasudorunas']
    member_count_out = ('%i object removed.', '%i objects removed.')

    def post_callback(self, ldap, completed, failed, dn, entry_attrs, *keys, **options):
        # Run through the user failures and gracefully remove any defined as
        # as an externaluser.
        if 'ipasudorunas' in failed and 'user' in failed['ipasudorunas']:
            (dn, entry_attrs_) = ldap.get_entry(dn, ['ipasudorunasextuser'])
            external_users = entry_attrs_.get('ipasudorunasextuser', [])
            failed_users = []
            completed_external = 0
            for user in failed['ipasudorunas']['user']:
                username = user[0].lower()
                if username in external_users:
                    external_users.remove(username)
                    completed_external += 1
                else:
                    failed_users.append(username)
            if completed_external:
                try:
                    ldap.update_entry(dn, {'ipasudorunasextuser': external_users})
                except errors.EmptyModlist:
                    pass
                failed['ipasudorunas']['user'] = failed_users
                entry_attrs['ipasudorunasextuser'] = external_users
        return (completed + completed_external, dn)

api.register(sudorule_remove_runasuser)


class sudorule_add_runasgroup(LDAPAddMember):
    __doc__ = _('Add group for Sudo to execute as.')

    member_attributes = ['ipasudorunasgroup']
    member_count_out = ('%i object added.', '%i objects added.')

    def post_callback(self, ldap, completed, failed, dn, entry_attrs, *keys, **options):
        completed_external = 0
        # Sift through the group failures. We assume that these are all
        # groups that aren't stored in IPA, aka external groups.
        if 'ipasudorunasgroup' in failed and 'group' in failed['ipasudorunasgroup']:
            (dn, entry_attrs_) = ldap.get_entry(dn, ['ipasudorunasextgroup'])
            members = entry_attrs.get('ipasudorunasgroup', [])
            external_groups = entry_attrs_.get('ipasudorunasextgroup', [])
            failed_groups = []
            for group in failed['ipasudorunasgroup']['group']:
                groupname = group[0].lower()
                group_dn = self.api.Object['group'].get_dn(groupname)
                if groupname not in external_groups and group_dn not in members:
                    external_groups.append(groupname)
                    completed_external += 1
                else:
                    failed_groups.append(groupname)
            if completed_external:
                try:
                    ldap.update_entry(dn, {'ipasudorunasextgroup': external_groups})
                except errors.EmptyModlist:
                    pass
                failed['ipasudorunasgroup']['group'] = failed_groups
                entry_attrs['ipasudorunasextgroup'] = external_groups
        return (completed + completed_external, dn)

api.register(sudorule_add_runasgroup)


class sudorule_remove_runasgroup(LDAPRemoveMember):
    __doc__ = _('Remove group for Sudo to execute as.')

    member_attributes = ['ipasudorunasgroup']
    member_count_out = ('%i object removed.', '%i objects removed.')

    def post_callback(self, ldap, completed, failed, dn, entry_attrs, *keys, **options):
        # Run through the group failures and gracefully remove any defined as
        # as an external group.
        if 'ipasudorunasgroup' in failed and 'group' in failed['ipasudorunasgroup']:
            (dn, entry_attrs_) = ldap.get_entry(dn, ['ipasudorunasextgroup'])
            external_groups = entry_attrs_.get('ipasudorunasextgroup', [])
            failed_groups = []
            completed_external = 0
            for group in failed['ipasudorunasgroup']['group']:
                groupname = group[0].lower()
                if groupname in external_groups:
                    external_groups.remove(groupname)
                    completed_external += 1
                else:
                    failed_groups.append(groupname)
            if completed_external:
                try:
                    ldap.update_entry(dn, {'ipasudorunasextgroup': external_groups})
                except errors.EmptyModlist:
                    pass
                failed['ipasudorunasgroup']['group'] = failed_groups
                entry_attrs['ipasudorunasextgroup'] = external_groups
        return (completed + completed_external, dn)

api.register(sudorule_remove_runasgroup)


class sudorule_add_option(LDAPQuery):
    __doc__ = _('Add an option to the Sudo Rule.')

    takes_options = (
        Str('ipasudoopt',
            cli_name='sudooption',
            label=_('Sudo Option'),
        ),
    )

    def execute(self, cn, **options):
        ldap = self.obj.backend

        dn = self.obj.get_dn(cn)

        if not options['ipasudoopt'].strip():
            raise errors.EmptyModlist()
        (dn, entry_attrs) = ldap.get_entry(dn, ['ipasudoopt'])

        try:
            if options['ipasudoopt'] not in entry_attrs['ipasudoopt']:
                entry_attrs.setdefault('ipasudoopt', []).append(
                    options['ipasudoopt'])
            else:
                raise errors.DuplicateEntry
        except KeyError:
            entry_attrs.setdefault('ipasudoopt', []).append(
                options['ipasudoopt'])
        try:
            ldap.update_entry(dn, entry_attrs)
        except errors.EmptyModlist:
            pass
        except errors.NotFound:
            self.obj.handle_not_found(cn)

        attrs_list = self.obj.default_attributes
        (dn, entry_attrs) = ldap.get_entry(
            dn, attrs_list, normalize=self.obj.normalize_dn
            )

        return dict(result=entry_attrs)

    def output_for_cli(self, textui, result, cn, **options):
        textui.print_dashed(_('Added option "%s" to Sudo Rule "%s"') % \
                (options['ipasudoopt'], cn))
        super(sudorule_add_option, self).output_for_cli(textui, result, cn, options)



api.register(sudorule_add_option)


class sudorule_remove_option(LDAPQuery):
    __doc__ = _('Remove an option from Sudo Rule.')

    takes_options = (
        Str('ipasudoopt',
            cli_name='sudooption',
            label=_('Sudo Option'),
        ),
    )

    def execute(self, cn, **options):
        ldap = self.obj.backend

        dn = self.obj.get_dn(cn)

        if not options['ipasudoopt'].strip():
            raise errors.EmptyModlist()
        (dn, entry_attrs) = ldap.get_entry(dn, ['ipasudoopt'])
        try:
            if options['ipasudoopt'] in entry_attrs['ipasudoopt']:
                entry_attrs.setdefault('ipasudoopt', []).remove(
                    options['ipasudoopt'])
                ldap.update_entry(dn, entry_attrs)
            else:
                raise errors.AttrValueNotFound(
                    attr='ipasudoopt',
                    value=options['ipasudoopt']
                    )
        except ValueError, e:
            pass
        except KeyError:
            raise errors.AttrValueNotFound(
                    attr='ipasudoopt',
                    value=options['ipasudoopt']
                    )
        except errors.NotFound:
            self.obj.handle_not_found(cn)

        attrs_list = self.obj.default_attributes
        (dn, entry_attrs) = ldap.get_entry(
            dn, attrs_list, normalize=self.obj.normalize_dn
            )

        return dict(result=entry_attrs)

    def output_for_cli(self, textui, result, cn, **options):
        textui.print_dashed(_('Removed option "%s" from Sudo Rule "%s"') % \
                (options['ipasudoopt'], cn))
        super(sudorule_remove_option, self).output_for_cli(textui, result, cn, options)

api.register(sudorule_remove_option)
