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
Test the `ipalib/plugins/sudocmdgroup.py` module.
"""

from ipalib import api, errors
from tests.test_xmlrpc import objectclasses
from xmlrpc_test import Declarative, fuzzy_digits, fuzzy_uuid

sudocmdgroup1 = u'testsudocmdgroup1'
sudocmdgroup2 = u'testsudocmdgroup2'
sudocmd1 = u'/usr/bin/sudotestcmd1'

class test_sudocmdgroup(Declarative):
    cleanup_commands = [
        ('sudocmdgroup_del', [sudocmdgroup1], {}),
        ('sudocmdgroup_del', [sudocmdgroup2], {}),
        ('sudocmd_del', [sudocmd1], {}),
    ]

    tests = [

        ################
        # create sudo command
        dict(
            desc='Create %r' % sudocmd1,
            command=(
                'sudocmd_add', [], dict(cn=sudocmd1,)
            ),
            expected=dict(
                value=sudocmd1,
                summary=u'Added sudo command "%s"' % sudocmd1,
                result=dict(
                    objectclass=objectclasses.sudocmd,
                    cn=[u'/usr/bin/sudotestcmd1'],
                    ipauniqueid=[fuzzy_uuid],
                    dn=u'cn=%s,cn=sudocmds,cn=accounts,%s' % (sudocmd1,
                        api.env.basedn),
                ),
            ),
        ),


        dict(
            desc='Verify the managed sudo command %r was created' % sudocmd1,
            command=('sudocmd_show', [sudocmd1], {}),
            expected=dict(
                value=sudocmd1,
                summary=None,
                result=dict(
                    cn=[sudocmd1],
                    dn=u'cn=%s,cn=sudocmds,cn=accounts,%s' % (sudocmd1,
                        api.env.basedn),
                ),
            ),
        ),


        ################
        # create sudo command group1:
        dict(
            desc='Try to retrieve non-existent %r' % sudocmdgroup1,
            command=('sudocmdgroup_show', [sudocmdgroup1], {}),
            expected=errors.NotFound(reason='no such entry'),
        ),


        dict(
            desc='Try to update non-existent %r' % sudocmdgroup1,
            command=('sudocmdgroup_mod', [sudocmdgroup1],
                dict(description=u'Foo')),
            expected=errors.NotFound(reason='no such entry'),
        ),


        dict(
            desc='Try to delete non-existent %r' % sudocmdgroup1,
            command=('sudocmdgroup_del', [sudocmdgroup1], {}),
            expected=errors.NotFound(reason='no such entry'),
        ),


        dict(
            desc='Create %r' % sudocmdgroup1,
            command=(
                'sudocmdgroup_add', [sudocmdgroup1],
                dict(description=u'Test desc 1')
            ),
            expected=dict(
                value=sudocmdgroup1,
                summary=u'Added sudo command group "testsudocmdgroup1"',
                result=dict(
                    cn=[sudocmdgroup1],
                    description=[u'Test desc 1'],
                    objectclass=objectclasses.sudocmdgroup,
                    ipauniqueid=[fuzzy_uuid],
                    dn=u'cn=testsudocmdgroup1,cn=sudocmdgroups,cn=accounts,' + \
                        api.env.basedn,
                ),
            ),
        ),


        dict(
            desc='Try to create duplicate %r' % sudocmdgroup1,
            command=(
                'sudocmdgroup_add', [sudocmdgroup1],
                dict(description=u'Test desc 1')
            ),
            expected=errors.DuplicateEntry(),
        ),


        dict(
            desc='Retrieve %r' % sudocmdgroup1,
            command=('sudocmdgroup_show', [sudocmdgroup1], {}),
            expected=dict(
                value=sudocmdgroup1,
                summary=None,
                result=dict(
                    cn=[sudocmdgroup1],
                    description=[u'Test desc 1'],
                    dn=u'cn=testsudocmdgroup1,cn=sudocmdgroups,cn=accounts,' + \
                        api.env.basedn,
                ),
            ),
        ),


        dict(
            desc='Updated %r' % sudocmdgroup1,
            command=(
                'sudocmdgroup_mod', [sudocmdgroup1],
                dict(description=u'New desc 1')
            ),
            expected=dict(
                result=dict(
                    cn=[sudocmdgroup1],
                    description=[u'New desc 1'],
                ),
                summary=u'Modified sudo command group "testsudocmdgroup1"',
                value=sudocmdgroup1,
            ),
        ),


        dict(
            desc='Retrieve %r to verify update' % sudocmdgroup1,
            command=('sudocmdgroup_show', [sudocmdgroup1], {}),
            expected=dict(
                value=sudocmdgroup1,
                result=dict(
                    cn=[sudocmdgroup1],
                    description=[u'New desc 1'],
                    dn=u'cn=testsudocmdgroup1,cn=sudocmdgroups,cn=accounts,' + \
                        api.env.basedn,
                ),
                summary=None,
            ),
        ),


        dict(
            desc='Search for %r' % sudocmdgroup1,
            command=('sudocmdgroup_find', [], dict(cn=sudocmdgroup1)),
            expected=dict(
                count=1,
                truncated=False,
                result=[
                    dict(
                        dn=u'cn=%s,cn=sudocmdgroups,cn=accounts,%s' % \
                            (sudocmdgroup1, api.env.basedn),
                        cn=[sudocmdgroup1],
                        description=[u'New desc 1'],
                    ),
                ],
                summary=u'1 sudo command group matched',
            ),
        ),



        ################
        # create sudocmdgroup2:
        dict(
            desc='Try to retrieve non-existent %r' % sudocmdgroup2,
            command=('sudocmdgroup_show', [sudocmdgroup2], {}),
            expected=errors.NotFound(reason='no such entry'),
        ),


        dict(
            desc='Try to update non-existent %r' % sudocmdgroup2,
            command=('sudocmdgroup_mod', [sudocmdgroup2],
                dict(description=u'Foo')),
            expected=errors.NotFound(reason='no such entry'),
        ),


        dict(
            desc='Try to delete non-existent %r' % sudocmdgroup2,
            command=('sudocmdgroup_del', [sudocmdgroup2], {}),
            expected=errors.NotFound(reason='no such entry'),
        ),


        dict(
            desc='Create %r' % sudocmdgroup2,
            command=(
                'sudocmdgroup_add', [sudocmdgroup2],
                dict(description=u'Test desc 2')
            ),
            expected=dict(
                value=sudocmdgroup2,
                summary=u'Added sudo command group "testsudocmdgroup2"',
                result=dict(
                    cn=[sudocmdgroup2],
                    description=[u'Test desc 2'],
                    objectclass=objectclasses.sudocmdgroup,
                    ipauniqueid=[fuzzy_uuid],
                    dn=u'cn=testsudocmdgroup2,cn=sudocmdgroups,cn=accounts,' + \
                        api.env.basedn,
                ),
            ),
        ),


        dict(
            desc='Try to create duplicate %r' % sudocmdgroup2,
            command=(
                'sudocmdgroup_add', [sudocmdgroup2],
                dict(description=u'Test desc 2')
            ),
            expected=errors.DuplicateEntry(),
        ),


        dict(
            desc='Retrieve %r' % sudocmdgroup2,
            command=('sudocmdgroup_show', [sudocmdgroup2], {}),
            expected=dict(
                value=sudocmdgroup2,
                summary=None,
                result=dict(
                    cn=[sudocmdgroup2],
                    description=[u'Test desc 2'],
                    dn=u'cn=testsudocmdgroup2,cn=sudocmdgroups,cn=accounts,' + \
                        api.env.basedn,
                ),
            ),
        ),


        dict(
            desc='Updated %r' % sudocmdgroup2,
            command=(
                'sudocmdgroup_mod', [sudocmdgroup2],
                dict(description=u'New desc 2')
            ),
            expected=dict(
                result=dict(
                    cn=[sudocmdgroup2],
                    description=[u'New desc 2'],
                ),
                summary=u'Modified sudo command group "testsudocmdgroup2"',
                value=sudocmdgroup2,
            ),
        ),


        dict(
            desc='Retrieve %r to verify update' % sudocmdgroup2,
            command=('sudocmdgroup_show', [sudocmdgroup2], {}),
            expected=dict(
                value=sudocmdgroup2,
                result=dict(
                    cn=[sudocmdgroup2],
                    description=[u'New desc 2'],
                    dn=u'cn=testsudocmdgroup2,cn=sudocmdgroups,cn=accounts,' + \
                        api.env.basedn,
                ),
                summary=None,
            ),
        ),


        dict(
            desc='Search for %r' % sudocmdgroup2,
            command=('sudocmdgroup_find', [], dict(cn=sudocmdgroup2)),
            expected=dict(
                count=1,
                truncated=False,
                result=[
                    dict(
                        dn=u'cn=%s,cn=sudocmdgroups,cn=accounts,%s' % \
                            (sudocmdgroup2, api.env.basedn),
                        cn=[sudocmdgroup2],
                        description=[u'New desc 2'],
                    ),
                ],
                summary=u'1 sudo command group matched',
            ),
        ),


        dict(
            desc='Search for all sudocmdgroups',
            command=('sudocmdgroup_find', [], {}),
            expected=dict(
                summary=u'2 sudo command groups matched',
                count=2,
                truncated=False,
                result=[
                    dict(
                        dn=u'cn=%s,cn=sudocmdgroups,cn=accounts,%s' % \
                            (sudocmdgroup1, api.env.basedn),
                        cn=[sudocmdgroup1],
                        description=[u'New desc 1'],
                    ),
                    dict(
                        dn=u'cn=%s,cn=sudocmdgroups,cn=accounts,%s' % \
                            (sudocmdgroup2, api.env.basedn),
                        cn=[sudocmdgroup2],
                        description=[u'New desc 2'],
                    ),
                ],
            ),
        ),



        ###############
        # member stuff:
        dict(
            desc='Add member %r to %r' % (sudocmd1, sudocmdgroup1),
            command=(
                'sudocmdgroup_add_member', [sudocmdgroup1],
                dict(sudocmd=sudocmd1)
            ),
            expected=dict(
                completed=1,
                failed=dict(
                    member=dict(
                        sudocmdgroup=tuple(),
                        sudocmd=tuple(),
                    ),
                ),
                result={
                        'dn': u'cn=%s,cn=sudocmdgroups,cn=accounts,%s' % \
                            (sudocmdgroup1, api.env.basedn),
                        'member_sudocmd': (sudocmd1,),
                        'cn': [sudocmdgroup1],
                        'description': [u'New desc 1'],
                },
            ),
        ),

        dict(
            # FIXME: Shouldn't this raise a NotFound instead?
            desc='Try to add non-existent member to %r' % sudocmdgroup1,
            command=(
                'sudocmdgroup_add_member', [sudocmdgroup1],
                dict(sudocmd=u'notfound')
            ),
            expected=dict(
                completed=0,
                failed=dict(
                    member=dict(
                        sudocmdgroup=tuple(),
                        sudocmd=(u'notfound',),
                    ),
                ),
                result={
                        'dn': u'cn=%s,cn=sudocmdgroups,cn=accounts,%s' % \
                            (sudocmdgroup1, api.env.basedn),
                        'member_sudocmd': (u'/usr/bin/sudotestcmd1',),
                        'cn': [sudocmdgroup1],
                        'description': [u'New desc 1'],
                },
            ),
        ),

        dict(
            desc='Remove member %r from %r' % (sudocmd1, sudocmdgroup1),
            command=('sudocmdgroup_remove_member',
                [sudocmdgroup1], dict(sudocmd=sudocmd1)
            ),
            expected=dict(
                completed=1,
                failed=dict(
                    member=dict(
                        sudocmdgroup=tuple(),
                        sudocmd=tuple(),
                    ),
                ),
                result={
                    'dn': u'cn=%s,cn=sudocmdgroups,cn=accounts,%s' % \
                        (sudocmdgroup1, api.env.basedn),
                    'cn': [sudocmdgroup1],
                    'description': [u'New desc 1'],
                },
            ),
        ),

        dict(
            # FIXME: Shouldn't this raise a NotFound instead?
            desc='Try to remove non-existent member from %r' % sudocmdgroup1,
            command=('sudocmdgroup_remove_member',
                [sudocmdgroup1], dict(sudocmd=u'notfound')
            ),
            expected=dict(
                completed=0,
                failed=dict(
                    member=dict(
                        sudocmdgroup=tuple(),
                        sudocmd=(u'notfound',),
                    ),
                ),
                result={
                    'dn': u'cn=%s,cn=sudocmdgroups,cn=accounts,%s' % \
                        (sudocmdgroup1, api.env.basedn),
                    'cn': [sudocmdgroup1],
                    'description': [u'New desc 1'],
                },
            ),
        ),


        ################
        # delete sudocmdgroup1:
        dict(
            desc='Delete %r' % sudocmdgroup1,
            command=('sudocmdgroup_del', [sudocmdgroup1], {}),
            expected=dict(
                result=True,
                value=sudocmdgroup1,
                summary=u'Deleted sudo command group "testsudocmdgroup1"',
            )
        ),


        dict(
            desc='Try to delete non-existent %r' % sudocmdgroup1,
            command=('sudocmdgroup_del', [sudocmdgroup1], {}),
            expected=errors.NotFound(reason='no such entry'),
        ),


        dict(
            desc='Try to retrieve non-existent %r' % sudocmdgroup1,
            command=('sudocmdgroup_show', [sudocmdgroup1], {}),
            expected=errors.NotFound(reason='no such entry'),
        ),


        dict(
            desc='Try to update non-existent %r' % sudocmdgroup1,
            command=('sudocmdgroup_mod', [sudocmdgroup1],
            dict(description=u'Foo')),
            expected=errors.NotFound(reason='no such entry'),
        ),


        ################
        # delete sudocmdgroup2:
        dict(
            desc='Delete %r' % sudocmdgroup2,
            command=('sudocmdgroup_del', [sudocmdgroup2], {}),
            expected=dict(
                result=True,
                value=sudocmdgroup2,
                summary=u'Deleted sudo command group "testsudocmdgroup2"',
            )
        ),


        dict(
            desc='Try to delete non-existent %r' % sudocmdgroup2,
            command=('sudocmdgroup_del', [sudocmdgroup2], {}),
            expected=errors.NotFound(reason='no such entry'),
        ),


        dict(
            desc='Try to retrieve non-existent %r' % sudocmdgroup2,
            command=('sudocmdgroup_show', [sudocmdgroup2], {}),
            expected=errors.NotFound(reason='no such entry'),
        ),


        dict(
            desc='Try to update non-existent %r' % sudocmdgroup2,
            command=('sudocmdgroup_mod', [sudocmdgroup2],
            dict(description=u'Foo')),
            expected=errors.NotFound(reason='no such entry'),
        ),


        ##### clean up test Command

        dict(
            desc='Now delete the sudo command %r' % sudocmd1,
            command=('sudocmd_del', [sudocmd1], {}),
            expected=dict(
                result=True,
                value=sudocmd1,
                summary=u'Deleted sudo command "%s"' % sudocmd1,
            )
        ),


        dict(
            desc='Verify that %r is really gone' % sudocmd1,
            command=('sudocmd_show', [sudocmd1], {}),
            expected=errors.NotFound(reason='no such entry'),
        ),

    ]