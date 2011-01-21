/*  Authors:
 *    Endi Sukma Dewata <edewata@redhat.com>
 *
 * Copyright (C) 2010 Red Hat
 * see file 'COPYING' for use and warranty information
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

module('entity');

test('Testing IPA.entity_set_search_definition().', function() {

    var uid_callback = function() {
        return true;
    };

    IPA.entity_set_search_definition('user', [
        ['uid', 'Login', uid_callback]
    ]);

    var facet = IPA.entity_get_search_facet('user');
    ok(
        facet,
        'IPA.entity_get_search_facet(\'user\') is not null'
    );

    var column = facet.get_columns()[0];
    ok(
        column,
        'column is not null'
    );

    equals(
        column.name, 'uid',
        'column.name'
    );

    equals(
        column.label, 'Login',
        'column.label'
    );

    ok(
        column.setup,
        'column.setup not null'
    );

    ok(
        column.setup(),
        'column.setup() works'
    );
});

test('Testing ipa_facet_setup_views().', function() {

    var orig_switch_and_show_page = IPA.switch_and_show_page;
    IPA.ajax_options.async = false;

    IPA.init(
        'data',
        true,
        function(data, text_status, xhr) {
            ok(true, 'ipa_init() succeeded.');
        },
        function(xhr, text_status, error_thrown) {
            ok(false, 'ipa_init() failed: '+error_thrown);
        }
    );

    var entity = IPA.entity({
        'name': 'user'
    });

    IPA.add_entity(entity);

    var facet = IPA.search_facet({
        'name': 'search',
        'label': 'Search'
    });
    entity.add_facet(facet);

    entity.create_association_facets();

    var container = $('<div/>');

    entity.init();
    entity.setup(container);

    var counter = 0;
    IPA.switch_and_show_page = function(entity_name, facet_name, pkey) {
        counter++;
    };

    //Container now has two divs, one for the action panel one for content
    var action_panel = facet.get_action_panel();
    ok(action_panel.length, 'action panel exists');

    var ul = $('ul', action_panel);

    var views = ul.children();

    /*6 Views:
      one for each of 3 associations
      one for search
      one for details
      a blank one for the action controls*/
    equals(
        views.length, 6,
        'Checking number of views'
    );

    var li = views.first();
    ok(  li.children().first().hasClass('action-controls'),
        'Checking that first item in list is placement for controls'
    );

    li = li.next(); // skip action controls
    li = li.next(); // skip the header line for Member of

    var attribute_members = IPA.metadata['user'].attribute_members;
    for (var attribute_member in attribute_members) {
        var objects = attribute_members[attribute_member];
        for (var i = 0; i < objects.length; i++) {
            var object = objects[i];
            var title = attribute_member+'_'+object;

            li = li.next();
            var value = li.attr('title');
            equals(
                value, title,
                'Checking the '+title+' facet'
            );
        }
    }

    var pkey_input =  $('input[name=pkey]', action_panel);
    ok(pkey_input.length,'pkey input exists');
    var search_facets = $('li.search-facet', action_panel);
    equals(search_facets.length,0,'search facet should not show up  in action panel');
    var entity_facets = $('li.entity-facet', action_panel);
    /*No longer automatically adding details, so ony the assoc. facets */
    equals(entity_facets.length,4,'4 hidden entity facets in action panel');
    entity_facets.each(function() {
        ok( $(this).hasClass('entity-facet-disabled'),
            'entity facets are disabled');
    });

    for ( var entity_facet = entity_facets.first();
          entity_facet.length;
          entity_facet = entity_facet.next()){
        entity_facet.click();
    }

    equals(counter, 0, 'links are disabled');

    IPA.switch_and_show_page = orig_switch_and_show_page;
});

