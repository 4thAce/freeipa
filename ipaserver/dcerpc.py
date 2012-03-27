# Authors:
#     Alexander Bokovoy <abokovoy@redhat.com>
#
# Copyright (C) 2011  Red Hat
# see file 'COPYING' for use and warranty information
#
# Portions (C) Andrew Tridgell, Andrew Bartlett
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

# Make sure we only run this module at the server where samba4-python
# package is installed to avoid issues with unavailable modules

from ipalib.plugins.baseldap import *
from ipalib import api, Str, Password, DefaultFrom, _, ngettext, Object
from ipalib.parameters import Enum
from ipalib import Command
from ipalib import errors
from ipapython import ipautil
from ipalib import util

import os, string, struct, copy
import uuid
from samba import param
from samba import credentials
from samba.dcerpc import security, lsa, drsblobs, nbt
from samba.ndr import ndr_pack
from samba import net
import samba
import random
import ldap as _ldap
from Crypto.Cipher import ARC4

__doc__ = _("""
Classes to manage trust joins using DCE-RPC calls

The code in this module relies heavily on samba4-python package
and Samba4 python bindings.
""")

class ExtendedDNControl(_ldap.controls.RequestControl):
    def __init__(self):
        self.controlType = "1.2.840.113556.1.4.529"
        self.criticality = False
        self.integerValue = 1

    def encodeControlValue(self):
        return '0\x03\x02\x01\x01'

class TrustDomainInstance(object):

    def __init__(self, hostname, creds=None):
        self.parm = param.LoadParm()
        self.parm.load(os.path.join(ipautil.SHARE_DIR,"smb.conf.empty"))
        if len(hostname) > 0:
            self.parm.set('netbios name', hostname)
        self.creds = creds
        self.hostname = hostname
        self.info = {}
        self._pipe = None
        self._policy_handle = None
        self.read_only = False

    def __gen_lsa_connection(self, binding):
       if self.creds is None:
           raise errors.RequirementError(name='CIFS credentials object')
       try:
           result = lsa.lsarpc(binding, self.parm, self.creds)
           return result
       except:
           return None

    def __init_lsa_pipe(self, remote_host):
        """
        Try to initialize connection to the LSA pipe at remote host.
        This method tries consequently all possible transport options
        and selects one that works. See __gen_lsa_bindings() for details.

        The actual result may depend on details of existing credentials.
        For example, using signing causes NO_SESSION_KEY with Win2K8 and
        using kerberos against Samba with signing does not work.
        """
        # short-cut: if LSA pipe is initialized, skip completely
        if self._pipe:
            return

        bindings = self.__gen_lsa_bindings(remote_host)
        for binding in bindings:
            self._pipe = self.__gen_lsa_connection(binding)
            if self._pipe:
                break
        if self._pipe is None:
            raise errors.RequirementError(name='Working LSA pipe')

    def __gen_lsa_bindings(self, remote_host):
        """
        There are multiple transports to issue LSA calls. However, depending on a
        system in use they may be blocked by local operating system policies.
        Generate all we can use. __init_lsa_pipe() will try them one by one until
        there is one working.

        We try NCACN_NP before NCACN_IP_TCP and signed sessions before unsigned.
        """
        transports = (u'ncacn_np', u'ncacn_ip_tcp')
        options = ( u',', u'')
        binding_template=lambda x,y,z: u'%s:%s[%s]' % (x, y, z)
        return [binding_template(t, remote_host, o) for t in transports for o in options]

    def retrieve_anonymously(self, remote_host, discover_srv=False):
        """
        When retrieving DC information anonymously, we can't get SID of the domain
        """
        netrc = net.Net(creds=self.creds, lp=self.parm)
        if discover_srv:
            result = netrc.finddc(domain=remote_host, flags=nbt.NBT_SERVER_LDAP | nbt.NBT_SERVER_DS)
        else:
            result = netrc.finddc(address=remote_host, flags=nbt.NBT_SERVER_LDAP | nbt.NBT_SERVER_DS)
        if not result:
            return False
        self.info['name'] = unicode(result.domain_name)
        self.info['dns_domain'] = unicode(result.dns_domain)
        self.info['dns_forest'] = unicode(result.forest)
        self.info['guid'] = unicode(result.domain_uuid)

        # Netlogon response doesn't contain SID of the domain.
        # We need to do rootDSE search with LDAP_SERVER_EXTENDED_DN_OID control to reveal the SID
        ldap_uri = 'ldap://%s' % (result.pdc_dns_name)
        conn = _ldap.initialize(ldap_uri)
        conn.set_option(_ldap.OPT_SERVER_CONTROLS, [ExtendedDNControl()])
        result = None
        try:
            (objtype, res) = conn.search_s('', _ldap.SCOPE_BASE)[0]
            result = res['defaultNamingContext'][0]
            self.info['dns_hostname'] = res['dnsHostName'][0]
        except _ldap.LDAPError, e:
            print "LDAP error when connecting to %s: %s" % (unicode(result.pdc_name), str(e))

        if result:
           self.info['sid'] = self.parse_naming_context(result)
        return True

    def parse_naming_context(self, context):
        naming_ref = re.compile('.*<SID=(S-.*)>.*')
        return naming_ref.match(context).group(1)

    def retrieve(self, remote_host):
        self.__init_lsa_pipe(remote_host)

        objectAttribute = lsa.ObjectAttribute()
        objectAttribute.sec_qos = lsa.QosInfo()
        self._policy_handle = self._pipe.OpenPolicy2(u"", objectAttribute, security.SEC_FLAG_MAXIMUM_ALLOWED)
        result = self._pipe.QueryInfoPolicy2(self._policy_handle, lsa.LSA_POLICY_INFO_DNS)
        self.info['name'] = unicode(result.name.string)
        self.info['dns_domain'] = unicode(result.dns_domain.string)
        self.info['dns_forest'] = unicode(result.dns_forest.string)
        self.info['guid'] = unicode(result.domain_guid)
        self.info['sid'] = unicode(result.sid)

    def generate_auth(self, trustdom_secret):
        def arcfour_encrypt(key, data):
            c = ARC4.new(key)
            return c.encrypt(data)
        def string_to_array(what):
            blob = [0] * len(what)

            for i in range(len(what)):
                blob[i] = ord(what[i])
            return blob

        password_blob = string_to_array(trustdom_secret.encode('utf-16-le'))

        clear_value = drsblobs.AuthInfoClear()
        clear_value.size = len(password_blob)
        clear_value.password = password_blob

        clear_authentication_information = drsblobs.AuthenticationInformation()
        clear_authentication_information.LastUpdateTime = samba.unix2nttime(int(time.time()))
        clear_authentication_information.AuthType = lsa.TRUST_AUTH_TYPE_CLEAR
        clear_authentication_information.AuthInfo = clear_value

        authentication_information_array = drsblobs.AuthenticationInformationArray()
        authentication_information_array.count = 1
        authentication_information_array.array = [clear_authentication_information]

        outgoing = drsblobs.trustAuthInOutBlob()
        outgoing.count = 1
        outgoing.current = authentication_information_array

        confounder = [3]*512
        for i in range(512):
            confounder[i] = random.randint(0, 255)

        trustpass = drsblobs.trustDomainPasswords()
        trustpass.confounder = confounder

        trustpass.outgoing = outgoing
        trustpass.incoming = outgoing

        trustpass_blob = ndr_pack(trustpass)

        encrypted_trustpass = arcfour_encrypt(self._pipe.session_key, trustpass_blob)

        auth_blob = lsa.DATA_BUF2()
        auth_blob.size = len(encrypted_trustpass)
        auth_blob.data = string_to_array(encrypted_trustpass)

        auth_info = lsa.TrustDomainInfoAuthInfoInternal()
        auth_info.auth_blob = auth_blob
        self.auth_info = auth_info



    def establish_trust(self, another_domain, trustdom_secret):
        """
        Establishes trust between our and another domain
        Input: another_domain -- instance of TrustDomainInstance, initialized with #retrieve call
               trustdom_secret -- shared secred used for the trust
        """
        self.generate_auth(trustdom_secret)

        info = lsa.TrustDomainInfoInfoEx()
        info.domain_name.string = another_domain.info['dns_domain']
        info.netbios_name.string = another_domain.info['name']
        info.sid = security.dom_sid(another_domain.info['sid'])
        info.trust_direction = lsa.LSA_TRUST_DIRECTION_INBOUND | lsa.LSA_TRUST_DIRECTION_OUTBOUND
        info.trust_type = lsa.LSA_TRUST_TYPE_UPLEVEL
        info.trust_attributes = lsa.LSA_TRUST_ATTRIBUTE_FOREST_TRANSITIVE | lsa.LSA_TRUST_ATTRIBUTE_USES_RC4_ENCRYPTION

        try:
            dname = lsa.String()
            dname.string = another_domain.info['dns_domain']
            res = self._pipe.QueryTrustedDomainInfoByName(self._policy_handle, dname, lsa.LSA_TRUSTED_DOMAIN_INFO_FULL_INFO)
            self._pipe.DeleteTrustedDomain(self._policy_handle, res.info_ex.sid)
        except:
            pass
        self._pipe.CreateTrustedDomainEx2(self._policy_handle, info, self.auth_info, security.SEC_STD_DELETE)

class TrustDomainJoins(object):
    ATTR_FLATNAME = 'ipantflatname'

    def __init__(self, api):
        self.api = api
        self.local_domain = None
        self.remote_domain = None

        self.ldap = self.api.Backend.ldap2
        cn_trust_local = DN(('cn', self.api.env.domain), self.api.env.container_cifsdomains, self.api.env.basedn)
        (dn, entry_attrs) = self.ldap.get_entry(unicode(cn_trust_local), [self.ATTR_FLATNAME])
        self.local_flatname = entry_attrs[self.ATTR_FLATNAME][0]
        self.local_dn = dn

        self.__populate_local_domain()

    def __populate_local_domain(self):
        # Initialize local domain info using kerberos only
        ld = TrustDomainInstance(self.local_flatname)
        ld.creds = credentials.Credentials()
        ld.creds.set_kerberos_state(credentials.MUST_USE_KERBEROS)
        ld.creds.guess(ld.parm)
        ld.creds.set_workstation(ld.hostname)
        ld.retrieve(util.get_fqdn())
        self.local_domain = ld

    def __populate_remote_domain(self, realm, realm_server=None, realm_admin=None, realm_passwd=None):
        def get_instance(self):
            # Fetch data from foreign domain using password only
            rd = TrustDomainInstance('')
            rd.parm.set('workgroup', self.local_domain.info['name'])
            rd.creds = credentials.Credentials()
            rd.creds.set_kerberos_state(credentials.DONT_USE_KERBEROS)
            rd.creds.guess(rd.parm)
            return rd

        rd = get_instance(self)
        rd.creds.set_anonymous()
        rd.creds.set_workstation(self.local_domain.hostname)
        if realm_server is None:
            rd.retrieve_anonymously(realm, discover_srv=True)
        else:
            rd.retrieve_anonymously(realm_server, discover_srv=False)
        rd.read_only = True
        if realm_admin and realm_passwd:
            if 'name' in rd.info:
                auth_string = u"%s\%s%%%s" % (rd.info['name'], realm_admin, realm_passwd)
                td = get_instance(self)
                td.creds.parse_string(auth_string)
                td.creds.set_workstation(self.local_domain.hostname)
                if realm_server is None:
                    # we must have rd.info['dns_hostname'] then, part of anonymous discovery
                    td.retrieve(rd.info['dns_hostname'])
                else:
                    td.retrieve(realm_server)
                td.read_only = False
                self.remote_domain = td
                return
        # Otherwise, use anonymously obtained data
        self.remote_domain = rd

    def join_ad_full_credentials(self, realm, realm_server, realm_admin, realm_passwd):
        self.__populate_remote_domain(realm, realm_server, realm_admin, realm_passwd)
        if not self.remote_domain.read_only:
            trustdom_pass = samba.generate_random_password(128, 128)
            self.remote_domain.establish_trust(self.local_domain, trustdom_pass)
            self.local_domain.establish_trust(self.remote_domain, trustdom_pass)
            return dict(local=self.local_domain, remote=self.remote_domain)
        return None

    def join_ad_ipa_half(self, realm, realm_server, trustdom_passwd):
        self.__populate_remote_domain(realm, realm_server, realm_passwd=None)
        self.local_domain.establish_trust(self.remote_domain, trustdom_passwd)
        return dict(local=self.local_domain, remote=self.remote_domain)

