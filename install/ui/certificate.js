/*jsl:import ipa.js */

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

IPA.cert = {};

IPA.cert.BEGIN_CERTIFICATE = '-----BEGIN CERTIFICATE-----';
IPA.cert.END_CERTIFICATE   = '-----END CERTIFICATE-----';

IPA.cert.BEGIN_CERTIFICATE_REQUEST = '-----BEGIN CERTIFICATE REQUEST-----';
IPA.cert.END_CERTIFICATE_REQUEST   = '-----END CERTIFICATE REQUEST-----';

/*
 * Pre-compiled regular expression to match a PEM cert.
 *
 * regexp group 1: entire canonical cert (delimiters plus base64)
 * regexp group 2: base64 data inside PEM delimiters
 */
IPA.cert.PEM_CERT_REGEXP = RegExp('(-----BEGIN CERTIFICATE-----([^-]*)-----END CERTIFICATE-----)');

/*
 * Pre-compiled regular expression to match a CSR (Certificate Signing Request).
 * The delimiter "CERTIFICATE REQUEST" is the cononical standard, however some legacy
 * software will produce a delimiter with "NEW" in it, i.e. "NEW CERTIFICATE REQUEST"
 * This regexp will work with either form.
 *
 * regexp group 1: entire canonical CSR (delimiters plus base64)
 * regexp group 2: base64 data inside canonical CSR delimiters
 * regexp group 3: entire legacy CSR (delimiters plus base64)
 * regexp group 4: base64 data inside legacy CSR delimiters
 */
IPA.cert.PEM_CSR_REGEXP = RegExp('(-----BEGIN CERTIFICATE REQUEST-----([^-]*)-----END CERTIFICATE REQUEST-----)|(-----BEGIN NEW CERTIFICATE REQUEST-----([^-]*)-----END NEW CERTIFICATE REQUEST-----)');

IPA.cert.CERTIFICATE_STATUS_MISSING = 0;
IPA.cert.CERTIFICATE_STATUS_VALID   = 1;
IPA.cert.CERTIFICATE_STATUS_REVOKED = 2;

IPA.cert.CRL_REASON = [
    'unspecified',
    'key_compromise',
    'ca_compromise',
    'affiliation_changed',
    'superseded',
    'cessation_of_operation',
    'certificate_hold',
    null,
    'remove_from_crl',
    'privilege_withdrawn',
    'aa_compromise'
];

IPA.cert.parse_dn = function(dn) {

    var result = {};
    if (!dn) return result;

    // TODO: Use proper LDAP DN parser
    var rdns = dn.split(',');
    for (var i=0; i<rdns.length; i++) {
        var rdn = rdns[i];
        if (!rdn) continue;

        var parts = rdn.split('=');
        var name = $.trim(parts[0].toLowerCase());
        var value = $.trim(parts[1]);

        var old_value = result[name];
        if (!old_value) {
            result[name] = value;
        } else if (typeof old_value == "string") {
            result[name] = [old_value, value];
        } else {
            result[name].push(value);
        }
    }

    return result;
};

IPA.cert.pem_format_base64 = function(text) {
    /*
     * Input is assumed to be base64 possibly with embedded whitespace.
     * Format the base64 text such that it conforms to PEM, which is a
     * sequence of 64 character lines, except for the last line which
     * may be less than 64 characters. The last line does NOT have a
     * new line appended to it.
     */
    var formatted = "";

    /* Strip out any whitespace including line endings */
    text = text.replace(/\s*/g,"");

    /*
     * Break up into lines with 64 chars each.
     * Do not add a newline to final line.
     */
    for (var i = 0; i < text.length; i+=64) {
        formatted += text.substring(i, i+64);
        if (i+64 < text.length) {
            formatted += "\n";
        }
    }
    return (formatted);
};

IPA.cert.pem_cert_format = function(text) {
    /*
     * Input is assumed to be either PEM formated data or the
     * base64 encoding of DER binary certificate data. Return data
     * in PEM format. The function checks if the input text is PEM
     * formatted, if so it just returns the input text. Otherwise
     * the input is treated as base64 which is formatted to be PEM>
     */

    /*
     * Does the text already have the PEM delimiters?
     * If so just return the text unmodified.
     */
    if (text.match(IPA.cert.PEM_CERT_REGEXP)) {
        return text;
    }
    /* No PEM delimiters so format the base64 & add the delimiters. */
    return IPA.cert.BEGIN_CERTIFICATE + "\n" +
           IPA.cert.pem_format_base64(text) + "\n" +
           IPA.cert.END_CERTIFICATE;
};

IPA.cert.pem_csr_format = function(text) {
    /*
     * Input is assumed to be either PEM formated data or the base64
     * encoding of DER binary certificate request (csr) data. Return
     * data in PEM format. The function checks if the input text is
     * PEM formatted, if so it just returns the input text. Otherwise
     * the input is treated as base64 which is formatted to be PEM>
     */

    /*
     * Does the text already have the PEM delimiters?
     * If so just return the text unmodified.
     */
    if (text.match(IPA.cert.PEM_CSR_REGEXP)) {
        return text;
    }

    /* No PEM delimiters so format the base64 & add the delimiters. */
    return IPA.cert.BEGIN_CERTIFICATE_REQUEST + "\n" +
           IPA.cert.pem_format_base64(text) + "\n" +
           IPA.cert.END_CERTIFICATE_REQUEST;
};

IPA.cert.download_dialog = function(spec) {

    spec = spec || {};

    var that = IPA.dialog(spec);

    that.width = spec.width || 500;
    that.height = spec.height || 380;
    that.add_pem_delimiters = typeof spec.add_pem_delimiters == 'undefined' ? true : spec.add_pem_delimiters;

    that.certificate = spec.certificate || '';

    that.create_button({
        name: 'close',
        label: IPA.messages.buttons.close,
        click: function() {
            that.close();
        }
    });

    that.create = function() {
        var textarea = $('<textarea/>', {
            'class': 'certificate',
            readonly: 'yes'
        }).appendTo(that.container);

        var certificate = that.certificate;

        if (that.add_pem_delimiters) {
            certificate = IPA.cert.pem_cert_format(that.certificate);
        }

        textarea.val(certificate);
    };

    return that;
};

IPA.cert.revoke_dialog = function(spec) {

    spec = spec || {};

    var that = IPA.dialog(spec);

    that.width = spec.width || 500;
    that.height = spec.height || 300;

    that.revoke = spec.revoke;

    that.create_button({
        name: 'revoke',
        label: IPA.messages.buttons.revoke,
        click: function() {
            var values = {};
            values['reason'] = that.select.val();
            if (that.revoke) {
                that.revoke(values);
            }
            that.close();
        }
    });

    that.create_button({
        name: 'cancel',
        label: IPA.messages.buttons.cancel,
        click: function() {
            that.close();
        }
    });

    that.create = function() {

        var table = $('<table/>').appendTo(that.container);

        var tr = $('<tr/>').appendTo(table);

        var td = $('<td/>').appendTo(tr);
        td.append(IPA.messages.objects.cert.note+':');

        td = $('<td/>').appendTo(tr);
        td.append(IPA.messages.objects.cert.revoke_confirmation);

        tr = $('<tr/>').appendTo(table);

        td = $('<td/>').appendTo(tr);
        td.append(IPA.messages.objects.cert.reason+':');

        td = $('<td/>').appendTo(tr);

        that.select = $('<select/>').appendTo(td);
        for (var i=0; i<IPA.cert.CRL_REASON.length; i++) {
            var reason = IPA.cert.CRL_REASON[i];
            if (!reason) continue;
            $('<option/>', {
                'value': i,
                'html': IPA.messages.objects.cert[reason]
            }).appendTo(that.select);
        }
    };

    return that;
};

IPA.cert.restore_dialog = function(spec) {

    spec = spec || {};

    var that = IPA.dialog(spec);

    that.width = spec.width || 400;
    that.height = spec.height || 200;

    that.restore = spec.restore;

    that.create_button({
        name: 'restore',
        label: IPA.messages.buttons.restore,
        click: function() {
            var values = {};
            if (that.restore) {
                that.restore(values);
            }
            that.close();
        }
    });

    that.create_button({
        name: 'cancel',
        label: IPA.messages.buttons.cancel,
        click: function() {
            that.close();
        }
    });

    that.create = function() {
        that.container.append(
            IPA.messages.objects.cert.restore_confirmation);
    };

    return that;
};

IPA.cert.view_dialog = function(spec) {

    spec = spec || {};

    var that = IPA.dialog(spec);

    that.width = spec.width || 600;
    that.height = spec.height || 500;

    that.subject = IPA.cert.parse_dn(spec.subject);
    that.serial_number = spec.serial_number || '';
    that.serial_number_hex = spec.serial_number_hex || '';
    that.issuer = IPA.cert.parse_dn(spec.issuer);
    that.issued_on = spec.issued_on || '';
    that.expires_on = spec.expires_on || '';
    that.md5_fingerprint = spec.md5_fingerprint || '';
    that.sha1_fingerprint = spec.sha1_fingerprint || '';

    that.create_button({
        name: 'close',
        label: IPA.messages.buttons.close,
        click: function() {
            that.close();
        }
    });

    that.create = function() {

        var table = $('<table/>').appendTo(that.container);

        var tr = $('<tr/>').appendTo(table);
        $('<td/>', {
            'colspan': 2,
            'html': '<h3>'+IPA.messages.objects.cert.issued_to+'</h3>'
        }).appendTo(tr);

        tr = $('<tr/>').appendTo(table);
        $('<td>'+IPA.messages.objects.cert.common_name+':</td>').appendTo(tr);
        $('<td/>', {
            text: that.subject.cn
        }).appendTo(tr);

        tr = $('<tr/>').appendTo(table);
        $('<td>'+IPA.messages.objects.cert.organization+':</td>').appendTo(tr);
        $('<td/>', {
            text: that.subject.o
        }).appendTo(tr);

        tr = $('<tr/>').appendTo(table);
        $('<td>'+IPA.messages.objects.cert.organizational_unit+':</td>').appendTo(tr);
        $('<td/>', {
            text: that.subject.ou
        }).appendTo(tr);

        tr = $('<tr/>').appendTo(table);
        $('<td>'+IPA.messages.objects.cert.serial_number+':</td>').appendTo(tr);
        $('<td/>', {
            text: that.serial_number
        }).appendTo(tr);

        tr = $('<tr/>').appendTo(table);
        $('<td>'+IPA.messages.objects.cert.serial_number_hex+':</td>').appendTo(tr);
        $('<td/>', {
            text: that.serial_number_hex
        }).appendTo(tr);

        tr = $('<tr/>').appendTo(table);
        $('<td/>', {
            'colspan': 2,
            'html': '<h3>'+IPA.messages.objects.cert.issued_by+'</h3>'
        }).appendTo(tr);

        tr = $('<tr/>').appendTo(table);
        $('<td>'+IPA.messages.objects.cert.common_name+':</td>').appendTo(tr);
        $('<td/>', {
            text: that.issuer.cn
        }).appendTo(tr);

        tr = $('<tr/>').appendTo(table);
        $('<td>'+IPA.messages.objects.cert.organization+':</td>').appendTo(tr);
        $('<td/>', {
            text: that.issuer.o
        }).appendTo(tr);

        tr = $('<tr/>').appendTo(table);
        $('<td>'+IPA.messages.objects.cert.organizational_unit+':</td>').appendTo(tr);
        $('<td/>', {
            text: that.issuer.ou
        }).appendTo(tr);

        tr = $('<tr/>').appendTo(table);
        $('<td/>', {
            'colspan': 2,
            'html': '<h3>'+IPA.messages.objects.cert.validity+'</h3>'
        }).appendTo(tr);

        tr = $('<tr/>').appendTo(table);
        $('<td>'+IPA.messages.objects.cert.issued_on+':</td>').appendTo(tr);
        $('<td/>', {
            text: that.issued_on
        }).appendTo(tr);

        tr = $('<tr/>').appendTo(table);
        $('<td>'+IPA.messages.objects.cert.expires_on+':</td>').appendTo(tr);
        $('<td/>', {
            text: that.expires_on
        }).appendTo(tr);

        tr = $('<tr/>').appendTo(table);
        $('<td/>', {
            'colspan': 2,
            'html': '<h3>'+IPA.messages.objects.cert.fingerprints+'</h3>'
        }).appendTo(tr);

        tr = $('<tr/>').appendTo(table);
        $('<td>'+IPA.messages.objects.cert.sha1_fingerprint+':</td>').appendTo(tr);
        $('<td/>', {
            text: that.sha1_fingerprint
        }).appendTo(tr);

        tr = $('<tr/>').appendTo(table);
        $('<td>'+IPA.messages.objects.cert.md5_fingerprint+':</td>').appendTo(tr);
        $('<td/>', {
            text: that.md5_fingerprint
        }).appendTo(tr);
    };

    return that;
};

IPA.cert.request_dialog = function(spec) {

    spec = spec || {};

    var that = IPA.dialog(spec);

    that.width = spec.width || 600;
    that.height = spec.height || 480;
    that.message = spec.message;

    that.request = spec.request;

    that.create_button({
        name: 'issue',
        label: IPA.messages.buttons.issue,
        click: function() {
            var values = {};
            var request = $.trim(that.textarea.val());
            request = IPA.cert.pem_csr_format(request);
            values['request'] = request;
            if (that.request) {
                that.request(values);
            }
            that.close();
        }
    });

    that.create_button({
        name: 'cancel',
        label: IPA.messages.buttons.cancel,
        click: function() {
            that.close();
        }
    });

    that.create = function() {
        that.container.append(that.message);

        that.textarea = $('<textarea/>', {
            'class': 'certificate'
        }).appendTo(that.container);
    };

    return that;
};

IPA.cert.status_widget = function(spec) {

    spec = spec || {};

    var that = IPA.input_widget(spec);

    that.entity_label = spec.entity_label || that.entity.metadata.label_singular;

    that.result = spec.result;

    that.get_entity_pkey = spec.get_entity_pkey;
    that.get_entity_name = spec.get_entity_name;
    that.get_entity_principal = spec.get_entity_principal;
    that.get_entity_certificate = spec.get_entity_certificate;

    that.is_selfsign = function() {
        return IPA.env.ra_plugin == 'selfsign';
    };

    that.create = function(container) {

        that.widget_create(container);

        var div = $('<div/>', {
            name: 'certificate-valid',
            style: 'display: none;'
        }).appendTo(container);

        $('<img/>', {
            src: 'images/check-icon.png',
            style: 'float: left;',
            'class': 'status-icon'
        }).appendTo(div);

        var content_div = $('<div/>', {
            style: 'float: left;'
        }).appendTo(div);

        content_div.append('<b>'+IPA.messages.objects.cert.valid+':</b>');

        content_div.append(' ');

        $('<input/>', {
            'type': 'button',
            'name': 'get',
            'value': IPA.messages.buttons.get
        }).appendTo(content_div);

        content_div.append(' ');

        if (!that.is_selfsign()) {
            $('<input/>', {
                'type': 'button',
                'name': 'revoke',
                'value': IPA.messages.buttons.revoke
            }).appendTo(content_div);

            content_div.append(' ');
        }

        $('<input/>', {
            'type': 'button',
            'name': 'view',
            'value': IPA.messages.buttons.view
        }).appendTo(content_div);

        content_div.append(' ');

        $('<input/>', {
            'type': 'button',
            'name': 'create',
            'value': IPA.messages.objects.cert.new_certificate
        }).appendTo(content_div);

        if (!that.is_selfsign()) {
            div = $('<div/>', {
                name: 'certificate-revoked',
                style: 'display: none;'
            }).appendTo(container);

            $('<img/>', {
                src: 'images/caution-icon.png',
                style: 'float: left;',
                'class': 'status-icon'
            }).appendTo(div);

            content_div = $('<div/>', {
                style: 'float: left;'
            }).appendTo(div);

            content_div.append('<b>'+IPA.messages.objects.cert.revoked+':</b>');

            content_div.append(' ');

            content_div.append($('<span/>', {
                'name': 'revocation_reason'
            }));

            content_div.append(' ');

            $('<input/>', {
                'type': 'button',
                'name': 'restore',
                'value': IPA.messages.buttons.restore
            }).appendTo(content_div);

            content_div.append(' ');

            $('<input/>', {
                'type': 'button',
                'name': 'create',
                'value': IPA.messages.objects.cert.new_certificate
            }).appendTo(content_div);
        }

        div = $('<div/>', {
            name: 'certificate-missing',
            style: 'display: none;'
        }).appendTo(container);

        $('<img/>', {
            src: 'images/caution-icon.png',
            style: 'float: left;',
            'class': 'status-icon'
        }).appendTo(div);

        content_div = $('<div/>', {
            style: 'float: left;'
        }).appendTo(div);

        content_div.append('<b>'+IPA.messages.objects.cert.missing+':</b>');

        content_div.append(' ');

        $('<input/>', {
            'type': 'button',
            'name': 'create',
            'value': IPA.messages.objects.cert.new_certificate
        }).appendTo(content_div);


        that.status_valid = $('div[name=certificate-valid]', that.container);
        that.status_revoked = $('div[name=certificate-revoked]', that.container);
        that.status_missing = $('div[name=certificate-missing]', that.container);

        var button = $('input[name=get]', that.container);
        that.get_button = IPA.button({
            name: 'get',
            label: IPA.messages.buttons.get,
            click: function() {
                IPA.command({
                    entity: that.entity.name,
                    method: 'show',
                    args: [that.pkey],
                    on_success: function(data, text_status, xhr) {
                        get_certificate(data.result.result);
                    }
                }).execute();
                return false;
            }
        });
        button.replaceWith(that.get_button);

        button = $('input[name=revoke]', that.container);
        that.revoke_button = IPA.button({
            name: 'revoke',
            label: IPA.messages.buttons.revoke,
            click: function() {
                IPA.command({
                    entity: that.entity.name,
                    method: 'show',
                    args: [that.pkey],
                    on_success: function(data, text_status, xhr) {
                        revoke_certificate(data.result.result);
                    }
                }).execute();
                return false;
            }
        });
        button.replaceWith(that.revoke_button);

        button = $('input[name=view]', that.container);
        that.view_button = IPA.button({
            name: 'view',
            label: IPA.messages.buttons.view,
            click: function() {
                IPA.command({
                    entity: that.entity.name,
                    method: 'show',
                    args: [that.pkey],
                    on_success: function(data, text_status, xhr) {
                        view_certificate(data.result.result);
                    }
                }).execute();
                return false;
            }
        });
        button.replaceWith(that.view_button);

        that.revocation_reason = $('span[name=revocation_reason]', that.container);

        button = $('input[name=restore]', that.container);
        that.restore_button = IPA.button({
            name: 'restore',
            label: IPA.messages.buttons.restore,
            click: function() {
                IPA.command({
                    entity: that.entity.name,
                    method: 'show',
                    args: [that.pkey],
                    on_success: function(data, text_status, xhr) {
                        restore_certificate(data.result.result);
                    }
                }).execute();
                return false;
            }
        });
        button.replaceWith(that.restore_button);

        $('input[name=create]', that.container).each(function(index) {
            button = $(this);
            that.create_button = IPA.button({
                name: 'create',
                label: IPA.messages.objects.cert.new_certificate,
                click: function() {
                    request_certificate(that.result);
                    return false;
                }
            });
            button.replaceWith(that.create_button);
        });
    };

    that.update = function() {

        that.pkey = that.get_entity_pkey(that.result);

        var entity_certificate = that.get_entity_certificate(that.result);
        if (entity_certificate) {
            check_status(that.result.serial_number);
        } else {
            set_status(IPA.cert.CERTIFICATE_STATUS_MISSING);
        }
    };

    that.clear = function() {
        that.status_valid.css('display', 'none');
        that.status_missing.css('display', 'none');
        that.status_revoked.css('display', 'none');
        that.revoke_button.css('display', 'none');
        that.restore_button.css('display', 'none');
        that.revocation_reason.text('');
    };

    function set_status(status, revocation_reason) {
        that.status_valid.css('display', status == IPA.cert.CERTIFICATE_STATUS_VALID ? '' : 'none');
        that.status_missing.css('display', status == IPA.cert.CERTIFICATE_STATUS_MISSING ? '' : 'none');

        if (!that.is_selfsign()) {
            that.status_revoked.css('display', status == IPA.cert.CERTIFICATE_STATUS_REVOKED ? '' : 'none');
            that.revoke_button.css('display', status == IPA.cert.CERTIFICATE_STATUS_VALID ? '' : 'none');

            var reason = IPA.cert.CRL_REASON[revocation_reason];
            that.revocation_reason.html(revocation_reason === undefined || reason === null ? '' : IPA.messages.objects.cert[reason]);
            that.restore_button.css('display', reason == 'certificate_hold' ? '' : 'none');
        }
    }

    function check_status(serial_number) {

        if (that.is_selfsign()) {
            set_status(IPA.cert.CERTIFICATE_STATUS_VALID);
            return;
        }

        IPA.command({
            entity: 'cert',
            method: 'show',
            args: [serial_number],
            on_success: function(data, text_status, xhr) {
                var revocation_reason = data.result.result.revocation_reason;
                if (revocation_reason == undefined) {
                    set_status(IPA.cert.CERTIFICATE_STATUS_VALID);
                } else {
                    set_status(IPA.cert.CERTIFICATE_STATUS_REVOKED, revocation_reason);
                }
            }
        }).execute();
    }

    function view_certificate(result) {

        var entity_certificate = that.get_entity_certificate(result);
        if (!entity_certificate) {
            set_status(IPA.cert.CERTIFICATE_STATUS_MISSING);
            return;
        }

        var entity_name = that.get_entity_name(result);

        var title = IPA.messages.objects.cert.view_certificate;
        title = title.replace('${entity}', that.entity_label);
        title = title.replace('${primary_key}', entity_name);

        var dialog = IPA.cert.view_dialog({
            'title': title,
            'subject': result['subject'],
            'serial_number': result['serial_number'],
            'serial_number_hex': result['serial_number_hex'],
            'issuer': result['issuer'],
            'issued_on': result['valid_not_before'],
            'expires_on': result['valid_not_after'],
            'md5_fingerprint': result['md5_fingerprint'],
            'sha1_fingerprint': result['sha1_fingerprint']
        });

        dialog.open();
    }

    function get_certificate(result) {

        var entity_certificate = that.get_entity_certificate(result);
        if (!entity_certificate) {
            set_status(IPA.cert.CERTIFICATE_STATUS_MISSING);
            return;
        }

        var entity_name = that.get_entity_name(result);

        var title = IPA.messages.objects.cert.view_certificate;
        title = title.replace('${entity}', that.entity_label);
        title = title.replace('${primary_key}', entity_name);

        var dialog = IPA.cert.download_dialog({
            title: title,
            certificate: entity_certificate
        });

        dialog.open();
    }

    function request_certificate(result) {

        var entity_name = that.get_entity_name(result);
        var entity_principal = that.get_entity_principal(result);

        var title = IPA.messages.objects.cert.issue_certificate;
        title = title.replace('${entity}', that.entity_label);
        title = title.replace('${primary_key}', entity_name);

        var dialog = IPA.cert.request_dialog({
            title: title,
            message: that.request_message,
            request: function(values) {
                var request = values['request'];

                IPA.command({
                    entity: 'cert',
                    method: 'request',
                    args: [request],
                    options: {
                        'principal': entity_principal
                    },
                    on_success: function(data, text_status, xhr) {
                        check_status(data.result.result.serial_number);
                    }
                }).execute();
            }
        });

        dialog.open();
    }

    function revoke_certificate(result) {

        var entity_certificate = that.get_entity_certificate(result);
        if (!entity_certificate) {
            set_status(IPA.cert.CERTIFICATE_STATUS_MISSING);
            return;
        }

        var entity_name = that.get_entity_name(result);
        var serial_number = result['serial_number'];

        var title = IPA.messages.objects.cert.revoke_certificate;
        title = title.replace('${entity}', that.entity_label);
        title = title.replace('${primary_key}', entity_name);

        var dialog = IPA.cert.revoke_dialog({
            'title': title,
            'revoke': function(values) {
                var reason = values['reason'];

                IPA.command({
                    entity: 'cert',
                    method: 'revoke',
                    args: [serial_number],
                    options: {
                        'revocation_reason': reason
                    },
                    on_success: function(data, text_status, xhr) {
                        check_status(serial_number);
                    }
                }).execute();
            }
        });

        dialog.open();
    }

    function restore_certificate(result) {

        var entity_certificate = that.get_entity_certificate(result);
        if (!entity_certificate) {
            set_status(IPA.cert.CERTIFICATE_STATUS_MISSING);
            return;
        }

        var entity_name = that.get_entity_name(result);
        var serial_number = result['serial_number'];

        var title = IPA.messages.objects.cert.restore_certificate;
        title = title.replace('${entity}', that.entity_label);
        title = title.replace('${primary_key}', entity_name);

        var dialog = IPA.cert.restore_dialog({
            'title': title,
            'restore': function(values) {
                IPA.command({
                    entity: 'cert',
                    method: 'remove_hold',
                    args: [serial_number],
                    on_success: function(data, text_status, xhr) {
                        check_status(serial_number);
                    }
                }).execute();
            }
        });

        dialog.open();
    }

    return that;
};

IPA.cert.status_field = function(spec) {

    spec = spec || {};

    var that = IPA.field(spec);

    that.load = function(result) {

        that.widget.result = result;
        that.reset();
    };

    return that;
};
