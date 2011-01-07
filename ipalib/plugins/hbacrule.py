# Authors:
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
Host-based access control

Control who can access what services on what hosts and from where. You
can use HBAC to control which users or groups on a source host can
access a service, or group of services, on a target host.

You can also specify a category of users, target hosts, and source
hosts. This is currently limited to "all", but might be expanded in the
future.

Target hosts and source hosts in HBAC rules must be hosts managed by IPA.

The available services and groups of services are controlled by the
hbacsvc and hbacsvcgroup plug-ins respectively.

EXAMPLES:

 Create a rule, "test1", that grants all users access to the host "server" from
 anywhere:
   ipa hbacrule-add --type=allow --usercat=all --srchostcat=all test1
   ipa hbacrule-add-host --hosts=server.example.com test1

 Display the properties of a named HBAC rule:
   ipa hbacrule-show test1

 Create a rule for a specific service. This lets the user john access
 the sshd service on any machine from any machine:
   ipa hbacrule-add --type=allow --hostcat=all --srchostcat=all john_sshd
   ipa hbacrule-add-user --users=john john_sshd
   ipa hbacrule-add-service --hbacsvcs=sshd john_sshd

 Create a rule for a new service group. This lets the user john access
 the any FTP service on any machine from any machine:
   ipa hbacsvcgroup-add ftpers
   ipa hbacsvc-add sftp
   ipa hbacsvcgroup-add-member --hbacsvcs=ftp,sftp ftpers
   ipa hbacrule-add --type=allow --hostcat=all --srchostcat=all john_ftp
   ipa hbacrule-add-user --users=john john_ftp
   ipa hbacrule-add-service --hbacsvcgroups=ftpers john_ftp

 Disable a named HBAC rule:
   ipa hbacrule-disable test1

 Remove a named HBAC rule:
   ipa hbacrule-del allow_server
"""


# AccessTime support is being removed for now.
#
# You can also control the times that the rule is active.
#
# The access time(s) of a host are cumulative and are not guaranteed to be
# applied in the order displayed.
#
# Specify that the rule "test1" be active every day between 0800 and 1400:
#   ipa hbacrule-add-accesstime --time='periodic daily 0800-1400' test1
#
# Specify that the rule "test1" be active once, from 10:32 until 10:33 on
# December 16, 2010:
#   ipa hbacrule-add-accesstime --time='absolute 201012161032 ~ 201012161033' test1


from ipalib import api, errors
from ipalib import AccessTime, Password, Str, StrEnum
from ipalib.plugins.baseldap import *
from ipalib import _, ngettext

topic = ('hbac', 'Host based access control commands')

def is_all(options, attribute):
    """
    See if options[attribute] is lower-case 'all' in a safe way.
    """
    if attribute in options and \
        options[attribute] is not None and \
        options[attribute].lower() == 'all':
        return True
    else:
        return False


class hbacrule(LDAPObject):
    """
    HBAC object.
    """
    container_dn = api.env.container_hbac
    object_name = 'HBAC rule'
    object_name_plural = 'HBAC rules'
    object_class = ['ipaassociation', 'ipahbacrule']
    default_attributes = [
        'cn', 'accessruletype', 'ipaenabledflag',
        'description', 'usercategory', 'hostcategory',
        'sourcehostcategory', 'servicecategory', 'ipaenabledflag',
        'memberuser', 'sourcehost', 'memberhost', 'memberservice',
        'memberhostgroup',
    ]
    uuid_attribute = 'ipauniqueid'
    rdn_attribute = 'ipauniqueid'
    attribute_members = {
        'memberuser': ['user', 'group'],
        'memberhost': ['host', 'hostgroup'],
        'sourcehost': ['host', 'hostgroup'],
        'memberservice': ['hbacsvc', 'hbacsvcgroup'],
    }

    label = _('HBAC')

    takes_params = (
        Str('cn',
            cli_name='name',
            label=_('Rule name'),
            primary_key=True,
        ),
        StrEnum('accessruletype',
            cli_name='type',
            doc=_('Rule type (allow or deny)'),
            label=_('Rule type'),
            values=(u'allow', u'deny'),
        ),
        # FIXME: {user,host,sourcehost,service}categories should expand in the future
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
        StrEnum('sourcehostcategory?',
            cli_name='srchostcat',
            label=_('Source host category'),
            doc=_('Source host category the rule applies to'),
            values=(u'all', ),
        ),
        StrEnum('servicecategory?',
            cli_name='servicecat',
            label=_('Service category'),
            doc=_('Service category the rule applies to'),
            values=(u'all', ),
        ),
#        AccessTime('accesstime?',
#            cli_name='time',
#            label=_('Access time'),
#        ),
        Str('description?',
            cli_name='desc',
            label=_('Description'),
        ),
        Flag('ipaenabledflag?',
             label=_('Enabled'),
             flags=['no_create', 'no_update', 'no_search'],
        ),
        Str('memberuser_user?',
            label=_('Users'),
            flags=['no_create', 'no_update', 'no_search'],
        ),
        Str('memberuser_group?',
            label=_('Groups'),
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
        Str('sourcehost_host?',
            label=_('Source hosts'),
            flags=['no_create', 'no_update', 'no_search'],
        ),
        Str('memberservice_hbacsvc?',
            label=_('Services'),
            flags=['no_create', 'no_update', 'no_search'],
        ),
        Str('memberservice_hbacsvcgroup?',
            label=_('Service Groups'),
            flags=['no_create', 'no_update', 'no_search'],
        ),
    )

api.register(hbacrule)


class hbacrule_add(LDAPCreate):
    """
    Create a new HBAC rule.
    """
    def pre_callback(self, ldap, dn, entry_attrs, attrs_list, *keys, **options):
        # HBAC rules are enabled by default
        entry_attrs['ipaenabledflag'] = 'TRUE'
        return dn

api.register(hbacrule_add)


class hbacrule_del(LDAPDelete):
    """
    Delete an HBAC rule.
    """

api.register(hbacrule_del)


class hbacrule_mod(LDAPUpdate):
    """
    Modify an HBAC rule.
    """

    def pre_callback(self, ldap, dn, entry_attrs, attrs_list, *keys, **options):
        try:
            (dn, entry_attrs) = ldap.get_entry(dn, attrs_list)
        except errors.NotFound:
            self.obj.handle_not_found(*keys)

        if is_all(options, 'usercategory') and 'memberuser' in entry_attrs:
            raise errors.MutuallyExclusiveError(reason="user category cannot be set to 'all' while there are allowed users")
        if is_all(options, 'hostcategory') and 'memberhost' in entry_attrs:
            raise errors.MutuallyExclusiveError(reason="host category cannot be set to 'all' while there are allowed hosts")
        if is_all(options, 'sourcehostcategory') and 'sourcehost' in entry_attrs:
            raise errors.MutuallyExclusiveError(reason="sourcehost category cannot be set to 'all' while there are allowed source hosts")
        if is_all(options, 'servicecategory') and 'memberservice' in entry_attrs:
            raise errors.MutuallyExclusiveError(reason="service category cannot be set to 'all' while there are allowed services")
        return dn

api.register(hbacrule_mod)


class hbacrule_find(LDAPSearch):
    """
    Search for HBAC rules.
    """

api.register(hbacrule_find)


class hbacrule_show(LDAPRetrieve):
    """
    Display the properties of an HBAC rule.
    """

api.register(hbacrule_show)


class hbacrule_enable(LDAPQuery):
    """
    Enable an HBAC rule.
    """
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
        textui.print_name(self.name)
        textui.print_dashed('Enabled HBAC rule "%s".' % cn)

api.register(hbacrule_enable)


class hbacrule_disable(LDAPQuery):
    """
    Disable an HBAC rule.
    """
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
        textui.print_name(self.name)
        textui.print_dashed('Disabled HBAC rule "%s".' % cn)

api.register(hbacrule_disable)


class hbacrule_add_accesstime(LDAPQuery):
    """
    Add an access time to an HBAC rule.
    """

    takes_options = (
        AccessTime('accesstime',
            cli_name='time',
            label=_('Access time'),
        ),
    )

    def execute(self, cn, **options):
        ldap = self.obj.backend

        dn = self.obj.get_dn(cn)

        (dn, entry_attrs) = ldap.get_entry(dn, ['accesstime'])
        entry_attrs.setdefault('accesstime', []).append(
            options['accesstime']
        )
        try:
            ldap.update_entry(dn, entry_attrs)
        except errors.EmptyModlist:
            pass
        except errors.NotFound:
            self.obj.handle_not_found(cn)

        return dict(result=True)

    def output_for_cli(self, textui, result, cn, **options):
        textui.print_name(self.name)
        textui.print_dashed(
            'Added access time "%s" to HBAC rule "%s"' % (
                options['accesstime'], cn
            )
        )

#api.register(hbacrule_add_accesstime)


class hbacrule_remove_accesstime(LDAPQuery):
    """
    Remove access time to HBAC rule.
    """
    takes_options = (
        AccessTime('accesstime?',
            cli_name='time',
            label=_('Access time'),
        ),
    )

    def execute(self, cn, **options):
        ldap = self.obj.backend

        dn = self.obj.get_dn(cn)

        (dn, entry_attrs) = ldap.get_entry(dn, ['accesstime'])
        try:
            entry_attrs.setdefault('accesstime', []).remove(
                options['accesstime']
            )
            ldap.update_entry(dn, entry_attrs)
        except (ValueError, errors.EmptyModlist):
            pass
        except errors.NotFound:
            self.obj.handle_not_found(cn)

        return dict(result=True)

    def output_for_cli(self, textui, result, cn, **options):
        textui.print_name(self.name)
        textui.print_dashed(
            'Removed access time "%s" from HBAC rule "%s"' % (
                options['accesstime'], cn
            )
        )

#api.register(hbacrule_remove_accesstime)


class hbacrule_add_user(LDAPAddMember):
    """
    Add users and groups to an HBAC rule.
    """
    member_attributes = ['memberuser']
    member_count_out = ('%i object added.', '%i objects added.')

    def pre_callback(self, ldap, dn, found, not_found, *keys, **options):
        (dn, entry_attrs) = ldap.get_entry(dn, self.obj.default_attributes)
        if 'usercategory' in entry_attrs and \
            entry_attrs['usercategory'][0].lower() == 'all':
            raise errors.MutuallyExclusiveError(reason="users cannot be added when user category='all'")
        return dn

api.register(hbacrule_add_user)


class hbacrule_remove_user(LDAPRemoveMember):
    """
    Remove users and groups from an HBAC rule.
    """
    member_attributes = ['memberuser']
    member_count_out = ('%i object removed.', '%i objects removed.')

api.register(hbacrule_remove_user)


class hbacrule_add_host(LDAPAddMember):
    """
    Add target hosts and hostgroups to an HBAC rule
    """
    member_attributes = ['memberhost']
    member_count_out = ('%i object added.', '%i objects added.')

    def pre_callback(self, ldap, dn, found, not_found, *keys, **options):
        (dn, entry_attrs) = ldap.get_entry(dn, self.obj.default_attributes)
        if 'hostcategory' in entry_attrs and \
            entry_attrs['hostcategory'][0].lower() == 'all':
            raise errors.MutuallyExclusiveError(reason="hosts cannot be added when host category='all'")
        return dn

api.register(hbacrule_add_host)


class hbacrule_remove_host(LDAPRemoveMember):
    """
    Remove target hosts and hostgroups from a HBAC rule.
    """
    member_attributes = ['memberhost']
    member_count_out = ('%i object removed.', '%i objects removed.')

api.register(hbacrule_remove_host)


class hbacrule_add_sourcehost(LDAPAddMember):
    """
    Add source hosts and hostgroups from a HBAC rule.
    """
    member_attributes = ['sourcehost']
    member_count_out = ('%i object added.', '%i objects added.')

    def pre_callback(self, ldap, dn, found, not_found, *keys, **options):
        (dn, entry_attrs) = ldap.get_entry(dn, self.obj.default_attributes)
        if 'sourcehostcategory' in entry_attrs and \
            entry_attrs['sourcehostcategory'][0].lower() == 'all':
            raise errors.MutuallyExclusiveError(reason="source hosts cannot be added when sourcehost category='all'")
        return dn

api.register(hbacrule_add_sourcehost)


class hbacrule_remove_sourcehost(LDAPRemoveMember):
    """
    Remove source hosts and hostgroups from an HBAC rule.
    """
    member_attributes = ['sourcehost']
    member_count_out = ('%i object removed.', '%i objects removed.')

api.register(hbacrule_remove_sourcehost)


class hbacrule_add_service(LDAPAddMember):
    """
    Add services to an HBAC rule.
    """
    member_attributes = ['memberservice']
    member_count_out = ('%i object added.', '%i objects added.')

    def pre_callback(self, ldap, dn, found, not_found, *keys, **options):
        (dn, entry_attrs) = ldap.get_entry(dn, self.obj.default_attributes)
        if 'servicecategory' in entry_attrs and \
            entry_attrs['servicecategory'][0].lower() == 'all':
            raise errors.MutuallyExclusiveError(reason="services cannot be added when service category='all'")
        return dn

api.register(hbacrule_add_service)


class hbacrule_remove_service(LDAPRemoveMember):
    """
    Remove source hosts and hostgroups from an HBAC rule.
    """
    member_attributes = ['memberservice']
    member_count_out = ('%i object removed.', '%i objects removed.')

api.register(hbacrule_remove_service)