# Authors:
#   Rob Crittenden <rcritten@redhat.com>
#   Pavel Zuna <pzuna@redhat.com>
#
# Copyright (C) 2008, 2009  Red Hat
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
Test the `ipalib.plugins.host` module.
"""

from ipalib import api, errors, x509
from ipalib.dn import *
from tests.test_xmlrpc.xmlrpc_test import Declarative, fuzzy_uuid, fuzzy_digits
from tests.test_xmlrpc.xmlrpc_test import fuzzy_hash, fuzzy_date, fuzzy_issuer
from tests.test_xmlrpc.xmlrpc_test import fuzzy_hex
from tests.test_xmlrpc import objectclasses
import base64


fqdn1 = u'testhost1.%s' % api.env.domain
short1 = u'testhost1'
dn1 = DN(('fqdn',fqdn1),('cn','computers'),('cn','accounts'),
         api.env.basedn)
service1 = u'dns/%s@%s' % (fqdn1, api.env.realm)
service1dn = DN(('krbprincipalname',service1.lower()),('cn','services'),
                ('cn','accounts'),api.env.basedn)
fqdn2 = u'shouldnotexist.%s' % api.env.domain
dn2 = DN(('fqdn',fqdn2),('cn','computers'),('cn','accounts'),
         api.env.basedn)
fqdn3 = u'testhost2.%s' % api.env.domain
short3 = u'testhost2'
dn3 = DN(('fqdn',fqdn3),('cn','computers'),('cn','accounts'),
         api.env.basedn)
fqdn4 = u'testhost2.lab.%s' % api.env.domain
dn4 = DN(('fqdn',fqdn4),('cn','computers'),('cn','accounts'),
         api.env.basedn)
invalidfqdn1 = u'foo_bar.lab.%s' % api.env.domain

# We can use the same cert we generated for the service tests
fd = open('tests/test_xmlrpc/service.crt', 'r')
servercert = fd.readlines()
servercert = ''.join(servercert)
servercert = x509.strip_header(servercert)
fd.close()

class test_host(Declarative):

    cleanup_commands = [
        ('host_del', [fqdn1], {}),
        ('host_del', [fqdn2], {}),
        ('host_del', [fqdn3], {}),
        ('host_del', [fqdn4], {}),
        ('service_del', [service1], {}),
    ]

    tests = [

        dict(
            desc='Try to retrieve non-existent %r' % fqdn1,
            command=('host_show', [fqdn1], {}),
            expected=errors.NotFound(
                reason=u'%s: host not found' % fqdn1),
        ),


        dict(
            desc='Try to update non-existent %r' % fqdn1,
            command=('host_mod', [fqdn1], dict(description=u'Nope')),
            expected=errors.NotFound(
                reason=u'%s: host not found' % fqdn1),
        ),


        dict(
            desc='Try to delete non-existent %r' % fqdn1,
            command=('host_del', [fqdn1], {}),
            expected=errors.NotFound(
                reason=u'%s: host not found' % fqdn1),
        ),


        dict(
            desc='Create %r' % fqdn1,
            command=('host_add', [fqdn1],
                dict(
                    description=u'Test host 1',
                    l=u'Undisclosed location 1',
                    force=True,
                ),
            ),
            expected=dict(
                value=fqdn1,
                summary=u'Added host "%s"' % fqdn1,
                result=dict(
                    dn=lambda x: DN(x) == dn1,
                    fqdn=[fqdn1],
                    description=[u'Test host 1'],
                    l=[u'Undisclosed location 1'],
                    krbprincipalname=[u'host/%s@%s' % (fqdn1, api.env.realm)],
                    objectclass=objectclasses.host,
                    ipauniqueid=[fuzzy_uuid],
                    managedby_host=[fqdn1],
                    has_keytab=False,
                    has_password=False,
                ),
            ),
        ),


        dict(
            desc='Try to create duplicate %r' % fqdn1,
            command=('host_add', [fqdn1],
                dict(
                    description=u'Test host 1',
                    locality=u'Undisclosed location 1',
                    force=True,
                ),
            ),
            expected=errors.DuplicateEntry(message=u'host with name ' +
                u'"%s" already exists' %  fqdn1),
        ),


        dict(
            desc='Retrieve %r' % fqdn1,
            command=('host_show', [fqdn1], {}),
            expected=dict(
                value=fqdn1,
                summary=None,
                result=dict(
                    dn=lambda x: DN(x) == dn1,
                    fqdn=[fqdn1],
                    description=[u'Test host 1'],
                    l=[u'Undisclosed location 1'],
                    krbprincipalname=[u'host/%s@%s' % (fqdn1, api.env.realm)],
                    has_keytab=False,
                    has_password=False,
                    managedby_host=[fqdn1],
                ),
            ),
        ),


        dict(
            desc='Retrieve %r with all=True' % fqdn1,
            command=('host_show', [fqdn1], dict(all=True)),
            expected=dict(
                value=fqdn1,
                summary=None,
                result=dict(
                    dn=lambda x: DN(x) == dn1,
                    cn=[fqdn1],
                    fqdn=[fqdn1],
                    description=[u'Test host 1'],
                    # FIXME: Why is 'localalityname' returned as 'l' with --all?
                    # It is intuitive for --all to return additional attributes,
                    # but not to return existing attributes under different
                    # names.
                    l=[u'Undisclosed location 1'],
                    krbprincipalname=[u'host/%s@%s' % (fqdn1, api.env.realm)],
                    serverhostname=[u'testhost1'],
                    objectclass=objectclasses.host,
                    managedby_host=[fqdn1],
                    managing_host=[fqdn1],
                    ipauniqueid=[fuzzy_uuid],
                    has_keytab=False,
                    has_password=False,
                ),
            ),
        ),


        dict(
            desc='Search for %r' % fqdn1,
            command=('host_find', [fqdn1], {}),
            expected=dict(
                count=1,
                truncated=False,
                summary=u'1 host matched',
                result=[
                    dict(
                        dn=lambda x: DN(x) == dn1,
                        fqdn=[fqdn1],
                        description=[u'Test host 1'],
                        l=[u'Undisclosed location 1'],
                        krbprincipalname=[u'host/%s@%s' % (fqdn1, api.env.realm)],
                        managedby_host=[u'%s' % fqdn1],
                        has_keytab=False,
                        has_password=False,
                    ),
                ],
            ),
        ),


        dict(
            desc='Search for %r with all=True' % fqdn1,
            command=('host_find', [fqdn1], dict(all=True)),
            expected=dict(
                count=1,
                truncated=False,
                summary=u'1 host matched',
                result=[
                    dict(
                        dn=lambda x: DN(x) == dn1,
                        cn=[fqdn1],
                        fqdn=[fqdn1],
                        description=[u'Test host 1'],
                        # FIXME: Why is 'localalityname' returned as 'l' with --all?
                        # It is intuitive for --all to return additional attributes,
                        # but not to return existing attributes under different
                        # names.
                        l=[u'Undisclosed location 1'],
                        krbprincipalname=[u'host/%s@%s' % (fqdn1, api.env.realm)],
                        serverhostname=[u'testhost1'],
                        objectclass=objectclasses.host,
                        ipauniqueid=[fuzzy_uuid],
                        managedby_host=[u'%s' % fqdn1],
                        managing_host=[u'%s' % fqdn1],
                        has_keytab=False,
                        has_password=False,
                    ),
                ],
            ),
        ),


        dict(
            desc='Update %r' % fqdn1,
            command=('host_mod', [fqdn1], dict(description=u'Updated host 1',
                usercertificate=servercert)),
            expected=dict(
                value=fqdn1,
                summary=u'Modified host "%s"' % fqdn1,
                result=dict(
                    description=[u'Updated host 1'],
                    fqdn=[fqdn1],
                    l=[u'Undisclosed location 1'],
                    krbprincipalname=[u'host/%s@%s' % (fqdn1, api.env.realm)],
                    managedby_host=[u'%s' % fqdn1],
                    usercertificate=[base64.b64decode(servercert)],
                    valid_not_before=fuzzy_date,
                    valid_not_after=fuzzy_date,
                    subject=lambda x: DN(x) == \
                        DN(('CN',api.env.host),x509.subject_base()),
                    serial_number=fuzzy_digits,
                    serial_number_hex=fuzzy_hex,
                    md5_fingerprint=fuzzy_hash,
                    sha1_fingerprint=fuzzy_hash,
                    issuer=fuzzy_issuer,
                    has_keytab=False,
                    has_password=False,
                ),
            ),
        ),


        dict(
            desc='Retrieve %r to verify update' % fqdn1,
            command=('host_show', [fqdn1], {}),
            expected=dict(
                value=fqdn1,
                summary=None,
                result=dict(
                    dn=lambda x: DN(x) == dn1,
                    fqdn=[fqdn1],
                    description=[u'Updated host 1'],
                    l=[u'Undisclosed location 1'],
                    krbprincipalname=[u'host/%s@%s' % (fqdn1, api.env.realm)],
                    has_keytab=False,
                    has_password=False,
                    managedby_host=[u'%s' % fqdn1],
                    usercertificate=[base64.b64decode(servercert)],
                    valid_not_before=fuzzy_date,
                    valid_not_after=fuzzy_date,
                    subject=lambda x: DN(x) == \
                        DN(('CN',api.env.host),x509.subject_base()),
                    serial_number=fuzzy_digits,
                    serial_number_hex=fuzzy_hex,
                    md5_fingerprint=fuzzy_hash,
                    sha1_fingerprint=fuzzy_hash,
                    issuer=fuzzy_issuer,
                ),
            ),
        ),

        dict(
            desc='Create %r' % fqdn3,
            command=('host_add', [fqdn3],
                dict(
                    description=u'Test host 2',
                    l=u'Undisclosed location 2',
                    force=True,
                ),
            ),
            expected=dict(
                value=fqdn3,
                summary=u'Added host "%s"' % fqdn3,
                result=dict(
                    dn=lambda x: DN(x) == dn3,
                    fqdn=[fqdn3],
                    description=[u'Test host 2'],
                    l=[u'Undisclosed location 2'],
                    krbprincipalname=[u'host/%s@%s' % (fqdn3, api.env.realm)],
                    objectclass=objectclasses.host,
                    ipauniqueid=[fuzzy_uuid],
                    managedby_host=[u'%s' % fqdn3],
                    has_keytab=False,
                    has_password=False,
                ),
            ),
        ),


        dict(
            desc='Create %r' % fqdn4,
            command=('host_add', [fqdn4],
                dict(
                    description=u'Test host 4',
                    l=u'Undisclosed location 4',
                    force=True,
                ),
            ),
            expected=dict(
                value=fqdn4,
                summary=u'Added host "%s"' % fqdn4,
                result=dict(
                    dn=lambda x: DN(x) == dn4,
                    fqdn=[fqdn4],
                    description=[u'Test host 4'],
                    l=[u'Undisclosed location 4'],
                    krbprincipalname=[u'host/%s@%s' % (fqdn4, api.env.realm)],
                    objectclass=objectclasses.host,
                    ipauniqueid=[fuzzy_uuid],
                    managedby_host=[u'%s' % fqdn4],
                    has_keytab=False,
                    has_password=False,
                ),
            ),
        ),


        dict(
            desc='Add managedby_host %r to %r' % (fqdn1, fqdn3),
            command=('host_add_managedby', [fqdn3],
                dict(
                    host=u'%s' % fqdn1,
                ),
            ),
            expected=dict(
                completed=1,
                failed=dict(
                    managedby = dict(
                        host=tuple(),
                    ),
                ),
                result=dict(
                    dn=lambda x: DN(x) == dn3,
                    fqdn=[fqdn3],
                    description=[u'Test host 2'],
                    l=[u'Undisclosed location 2'],
                    krbprincipalname=[u'host/%s@%s' % (fqdn3, api.env.realm)],
                    managedby_host=[u'%s' % fqdn3, u'%s' % fqdn1],
                ),
            ),
        ),

        dict(
            desc='Retrieve %r' % fqdn3,
            command=('host_show', [fqdn3], {}),
            expected=dict(
                value=fqdn3,
                summary=None,
                result=dict(
                    dn=lambda x: DN(x) == dn3,
                    fqdn=[fqdn3],
                    description=[u'Test host 2'],
                    l=[u'Undisclosed location 2'],
                    krbprincipalname=[u'host/%s@%s' % (fqdn3, api.env.realm)],
                    has_keytab=False,
                    has_password=False,
                    managedby_host=[u'%s' % fqdn3, u'%s' % fqdn1],
                ),
            ),
        ),

        dict(
            desc='Search for hosts with --man-hosts and --not-man-hosts',
            command=('host_find', [], {'man_host' : fqdn3, 'not_man_host' : fqdn1}),
            expected=dict(
                count=1,
                truncated=False,
                summary=u'1 host matched',
                result=[
                    dict(
                        dn=lambda x: DN(x) == dn3,
                        fqdn=[fqdn3],
                        description=[u'Test host 2'],
                        l=[u'Undisclosed location 2'],
                        krbprincipalname=[u'host/%s@%s' % (fqdn3, api.env.realm)],
                        has_keytab=False,
                        has_password=False,
                        managedby_host=[u'%s' % fqdn3, u'%s' % fqdn1],
                    ),
                ],
            ),
        ),

        dict(
            desc='Try to search for hosts with --man-hosts',
            command=('host_find', [], {'man_host' : [fqdn3,fqdn4]}),
            expected=dict(
                count=0,
                truncated=False,
                summary=u'0 hosts matched',
                result=[],
            ),
        ),

        dict(
            desc='Remove managedby_host %r from %r' % (fqdn1, fqdn3),
            command=('host_remove_managedby', [fqdn3],
                dict(
                    host=u'%s' % fqdn1,
                ),
            ),
            expected=dict(
                completed=1,
                failed=dict(
                    managedby = dict(
                        host=tuple(),
                    ),
                ),
                result=dict(
                    dn=lambda x: DN(x) == dn3,
                    fqdn=[fqdn3],
                    description=[u'Test host 2'],
                    l=[u'Undisclosed location 2'],
                    krbprincipalname=[u'host/%s@%s' % (fqdn3, api.env.realm)],
                    managedby_host=[u'%s' % fqdn3],
                ),
            ),
        ),


        dict(
            desc='Show a host with multiple matches %s' % short3,
            command=('host_show', [short3], {}),
            expected=errors.SingleMatchExpected(found=2),
        ),


        dict(
            desc='Try to rename %r' % fqdn1,
            command=('host_mod', [fqdn1], dict(setattr=u'fqdn=changed.example.com')),
            expected=errors.NotAllowedOnRDN()
        ),


        dict(
            desc='Add MAC address to %r' % fqdn1,
            command=('host_mod', [fqdn1], dict(macaddress=u'00:50:56:30:F6:5F')),
            expected=dict(
                value=fqdn1,
                summary=u'Modified host "%s"' % fqdn1,
                result=dict(
                    description=[u'Updated host 1'],
                    fqdn=[fqdn1],
                    l=[u'Undisclosed location 1'],
                    krbprincipalname=[u'host/%s@%s' % (fqdn1, api.env.realm)],
                    managedby_host=[u'%s' % fqdn1],
                    usercertificate=[base64.b64decode(servercert)],
                    valid_not_before=fuzzy_date,
                    valid_not_after=fuzzy_date,
                    subject=lambda x: DN(x) == \
                        DN(('CN',api.env.host),x509.subject_base()),
                    serial_number=fuzzy_digits,
                    serial_number_hex=fuzzy_hex,
                    md5_fingerprint=fuzzy_hash,
                    sha1_fingerprint=fuzzy_hash,
                    macaddress=[u'00:50:56:30:F6:5F'],
                    issuer=fuzzy_issuer,
                    has_keytab=False,
                    has_password=False,
                ),
            ),
        ),


        dict(
            desc='Add another MAC address to %r' % fqdn1,
            command=('host_mod', [fqdn1], dict(macaddress=[u'00:50:56:30:F6:5F', u'00:50:56:2C:8D:82'])),
            expected=dict(
                value=fqdn1,
                summary=u'Modified host "%s"' % fqdn1,
                result=dict(
                    description=[u'Updated host 1'],
                    fqdn=[fqdn1],
                    l=[u'Undisclosed location 1'],
                    krbprincipalname=[u'host/%s@%s' % (fqdn1, api.env.realm)],
                    managedby_host=[u'%s' % fqdn1],
                    usercertificate=[base64.b64decode(servercert)],
                    valid_not_before=fuzzy_date,
                    valid_not_after=fuzzy_date,
                    subject=lambda x: DN(x) == \
                        DN(('CN',api.env.host),x509.subject_base()),
                    serial_number=fuzzy_digits,
                    serial_number_hex=fuzzy_hex,
                    md5_fingerprint=fuzzy_hash,
                    sha1_fingerprint=fuzzy_hash,
                    macaddress=[u'00:50:56:30:F6:5F', u'00:50:56:2C:8D:82'],
                    issuer=fuzzy_issuer,
                    has_keytab=False,
                    has_password=False,
                ),
            ),
        ),


        dict(
            desc='Add an illegal MAC address to %r' % fqdn1,
            command=('host_mod', [fqdn1], dict(macaddress=[u'xx'])),
            expected=errors.ValidationError(name='macaddress',
                error=u'Must be of the form HH:HH:HH:HH:HH:HH, where ' +
                    u'each H is a hexadecimal character.'),
        ),


        dict(
            desc='Delete %r' % fqdn1,
            command=('host_del', [fqdn1], {}),
            expected=dict(
                value=fqdn1,
                summary=u'Deleted host "%s"' % fqdn1,
                result=dict(failed=u''),
            ),
        ),


        dict(
            desc='Try to retrieve non-existent %r' % fqdn1,
            command=('host_show', [fqdn1], {}),
            expected=errors.NotFound(reason=u'%s: host not found' % fqdn1),
        ),


        dict(
            desc='Try to update non-existent %r' % fqdn1,
            command=('host_mod', [fqdn1], dict(description=u'Nope')),
            expected=errors.NotFound(reason=u'%s: host not found' % fqdn1),
        ),


        dict(
            desc='Try to delete non-existent %r' % fqdn1,
            command=('host_del', [fqdn1], {}),
            expected=errors.NotFound(reason=u'%s: host not found' % fqdn1),
        ),

        # Test deletion using a non-fully-qualified hostname. Services
        # associated with this host should also be removed.
        dict(
            desc='Re-create %r' % fqdn1,
            command=('host_add', [fqdn1],
                dict(
                    description=u'Test host 1',
                    l=u'Undisclosed location 1',
                    force=True,
                ),
            ),
            expected=dict(
                value=fqdn1,
                summary=u'Added host "%s"' % fqdn1,
                result=dict(
                    dn=lambda x: DN(x) == dn1,
                    fqdn=[fqdn1],
                    description=[u'Test host 1'],
                    l=[u'Undisclosed location 1'],
                    krbprincipalname=[u'host/%s@%s' % (fqdn1, api.env.realm)],
                    objectclass=objectclasses.host,
                    ipauniqueid=[fuzzy_uuid],
                    managedby_host=[u'%s' % fqdn1],
                    has_keytab=False,
                    has_password=False,
                ),
            ),
        ),

        dict(
            desc='Add a service to host %r' % fqdn1,
            command=('service_add', [service1], {'force': True}),
            expected=dict(
                value=service1,
                summary=u'Added service "%s"' % service1,
                result=dict(
                    dn=lambda x: DN(x) == service1dn,
                    krbprincipalname=[service1],
                    objectclass=objectclasses.service,
                    managedby_host=[fqdn1],
                    ipauniqueid=[fuzzy_uuid],
                ),
            ),
        ),

        dict(
            desc='Delete using host name %r' % short1,
            command=('host_del', [short1], {}),
            expected=dict(
                value=short1,
                summary=u'Deleted host "%s"' % short1,
                result=dict(failed=u''),
            ),
        ),

        dict(
            desc='Search for services for %r' % fqdn1,
            command=('service_find', [fqdn1], {}),
            expected=dict(
                count=0,
                truncated=False,
                summary=u'0 services matched',
                result=[
                ],
            ),
        ),


        dict(
            desc='Try to add host not in DNS %r without force' % fqdn2,
            command=('host_add', [fqdn2], {}),
            expected=errors.DNSNotARecordError(
                reason=u'Host does not have corresponding DNS A record'),
        ),


        dict(
            desc='Try to add host not in DNS %r with force' % fqdn2,
            command=('host_add', [fqdn2],
                dict(
                    description=u'Test host 2',
                    l=u'Undisclosed location 2',
                    force=True,
                ),
            ),
            expected=dict(
                value=fqdn2,
                summary=u'Added host "%s"' % fqdn2,
                result=dict(
                    dn=lambda x: DN(x) == dn2,
                    fqdn=[fqdn2],
                    description=[u'Test host 2'],
                    l=[u'Undisclosed location 2'],
                    krbprincipalname=[u'host/%s@%s' % (fqdn2, api.env.realm)],
                    objectclass=objectclasses.host,
                    ipauniqueid=[fuzzy_uuid],
                    managedby_host=[fqdn2],
                    has_keytab=False,
                    has_password=False,
                ),
            ),
        ),


        # This test will only succeed when running against lite-server.py
        # on same box as IPA install.
        dict(
            desc='Delete the current host (master?) %s should be caught' % api.env.host,
            command=('host_del', [api.env.host], {}),
            expected=errors.ValidationError(name='hostname',
                error=u'An IPA master host cannot be deleted or disabled'),
        ),


        dict(
            desc='Disable the current host (master?) %s should be caught' % api.env.host,
            command=('host_disable', [api.env.host], {}),
            expected=errors.ValidationError(name='hostname',
                error=u'An IPA master host cannot be deleted or disabled'),
        ),


        dict(
            desc='Test that validation is enabled on adds',
            command=('host_add', [invalidfqdn1], {}),
            expected=errors.ValidationError(name='hostname',
                error=u'invalid domain-name: only letters, numbers, and - ' +
                    u'are allowed. DNS label may not start or end with -'),
        ),


        # The assumption on these next 4 tests is that if we don't get a
        # validation error then the request was processed normally.
        dict(
            desc='Test that validation is disabled on mods',
            command=('host_mod', [invalidfqdn1], {}),
            expected=errors.NotFound(
                reason=u'%s: host not found' % invalidfqdn1),
        ),


        dict(
            desc='Test that validation is disabled on deletes',
            command=('host_del', [invalidfqdn1], {}),
            expected=errors.NotFound(
                reason=u'%s: host not found' % invalidfqdn1),
        ),


        dict(
            desc='Test that validation is disabled on show',
            command=('host_show', [invalidfqdn1], {}),
            expected=errors.NotFound(
                reason=u'%s: host not found' % invalidfqdn1),
        ),


        dict(
            desc='Test that validation is disabled on find',
            command=('host_find', [invalidfqdn1], {}),
            expected=dict(
                count=0,
                truncated=False,
                summary=u'0 hosts matched',
                result=[],
            ),
        ),

    ]
