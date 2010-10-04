/** BEGIN COPYRIGHT BLOCK
 * This Program is free software; you can redistribute it and/or modify it under
 * the terms of the GNU General Public License as published by the Free Software
 * Foundation; version 2 of the License.
 *
 * This Program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details
 *
 * You should have received a copy of the GNU General Public License along with
 * this Program; if not, write to the Free Software Foundation, Inc., 59 Temple
 * Place, Suite 330, Boston, MA 02111-1307 USA.
 *
 * In addition, as a special exception, Red Hat, Inc. gives You the additional
 * right to link the code of this Program with code not covered under the GNU
 * General Public License ("Non-GPL Code") and to distribute linked combinations
 * including the two, subject to the limitations in this paragraph. Non-GPL Code
 * permitted under this exception must only link to the code of this Program
 * through those well defined interfaces identified in the file named EXCEPTION
 * found in the source code files (the "Approved Interfaces"). The files of
 * Non-GPL Code may instantiate templates or use macros or inline functions from
 * the Approved Interfaces without causing the resulting work to be covered by
 * the GNU General Public License. Only Red Hat, Inc. may make changes or
 * additions to the list of Approved Interfaces. You must obey the GNU General
 * Public License in all respects for all of the Program code and other code
 * used in conjunction with the Program except the Non-GPL Code covered by this
 * exception. If you modify this file, you may extend this exception to your
 * version of the file, but you are not obligated to do so. If you do not wish
 * to provide this exception without modification, you must delete this
 * exception statement from your version and license this file solely under the
 * GPL without exception.
 *
 * Authors:
 * Simo Sorce <ssorce@redhat.com>
 *
 * Copyright (C) 2007-2010 Red Hat, Inc.
 * All rights reserved.
 * END COPYRIGHT BLOCK **/

#ifdef HAVE_CONFIG_H
#  include <config.h>
#endif

#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>

#include <dirsrv/slapi-plugin.h>
#include <lber.h>
#include <time.h>

#include "ipapwd.h"

#define IPAPWD_OP_NULL 0
#define IPAPWD_OP_ADD 1
#define IPAPWD_OP_MOD 2

extern Slapi_PluginDesc ipapwd_plugin_desc;
extern void *ipapwd_plugin_id;
extern const char *ipa_realm_tree;

/* structure with information for each extension */
struct ipapwd_op_ext {
    char *object_name;   /* name of the object extended   */
    int object_type;     /* handle to the extended object */
    int handle;          /* extension handle              */
};
/*****************************************************************************
 * pre/post operations to intercept writes to userPassword
 ****************************************************************************/
static struct ipapwd_op_ext ipapwd_op_ext_list;

static void *ipapwd_op_ext_constructor(void *object, void *parent)
{
    struct ipapwd_operation *ext;

    ext = (struct ipapwd_operation *)slapi_ch_calloc(1, sizeof(struct ipapwd_operation));
    return ext;
}

static void ipapwd_op_ext_destructor(void *ext, void *object, void *parent)
{
    struct ipapwd_operation *pwdop = (struct ipapwd_operation *)ext;
    if (!pwdop)
        return;
    if (pwdop->pwd_op != IPAPWD_OP_NULL) {
        slapi_ch_free_string(&(pwdop->pwdata.dn));
        slapi_ch_free_string(&(pwdop->pwdata.password));
    }
    slapi_ch_free((void **)&pwdop);
}

int ipapwd_ext_init(void)
{
    int ret;

    ipapwd_op_ext_list.object_name = SLAPI_EXT_OPERATION;

    ret = slapi_register_object_extension(IPAPWD_PLUGIN_NAME,
                                          SLAPI_EXT_OPERATION,
                                          ipapwd_op_ext_constructor,
                                          ipapwd_op_ext_destructor,
                                          &ipapwd_op_ext_list.object_type,
                                          &ipapwd_op_ext_list.handle);

    return ret;
}


static char *ipapwd_getIpaConfigAttr(const char *attr)
{
    /* check if migrtion is enabled */
    Slapi_Entry *entry = NULL;
    const char *attrs_list[] = {attr, 0};
    char *value = NULL;
    char *dn = NULL;
    int ret;

    dn = slapi_ch_smprintf("cn=ipaconfig,cn=etc,%s", ipa_realm_tree);
    if (!dn) {
        slapi_log_error(SLAPI_LOG_FATAL, IPAPWD_PLUGIN_NAME,
                        "Out of memory ?\n");
        goto done;
    }

    ret = ipapwd_getEntry(dn, &entry, (char **) attrs_list);
    if (ret) {
        slapi_log_error(SLAPI_LOG_PLUGIN, IPAPWD_PLUGIN_NAME,
                        "failed to retrieve config entry: %s\n", dn);
        goto done;
    }

    value = slapi_entry_attr_get_charptr(entry, attr);

done:
    slapi_entry_free(entry);
    slapi_ch_free_string(&dn);
    return value;
}


/* PRE ADD Operation:
 * Gets the clean text password (fail the operation if the password came
 * pre-hashed, unless this is a replicated operation or migration mode is
 * enabled).
 * Check user is authorized to add it otherwise just returns, operation will
 * fail later anyway.
 * Run a password policy check.
 * Check if krb or smb hashes are required by testing if the krb or smb
 * objectclasses are present.
 * store information for the post operation
 */
static int ipapwd_pre_add(Slapi_PBlock *pb)
{
    struct ipapwd_krbcfg *krbcfg = NULL;
    char *errMesg = "Internal operations error\n";
    struct slapi_entry *e = NULL;
    char *userpw = NULL;
    char *dn = NULL;
    struct ipapwd_operation *pwdop = NULL;
    void *op;
    int is_repl_op, is_root, is_krb, is_smb;
    int ret;
    int rc = LDAP_SUCCESS;

    slapi_log_error(SLAPI_LOG_TRACE, IPAPWD_PLUGIN_NAME, "=> ipapwd_pre_add\n");

    ret = slapi_pblock_get(pb, SLAPI_IS_REPLICATED_OPERATION, &is_repl_op);
    if (ret != 0) {
        slapi_log_error(SLAPI_LOG_FATAL, IPAPWD_PLUGIN_NAME,
                        "slapi_pblock_get failed!?\n");
        rc = LDAP_OPERATIONS_ERROR;
        goto done;
    }

    /* pass through if this is a replicated operation */
    if (is_repl_op)
        return 0;

    /* retrieve the entry */
    slapi_pblock_get(pb, SLAPI_ADD_ENTRY, &e);
    if (NULL == e)
        return 0;

    /* check this is something interesting for us first */
    userpw = slapi_entry_attr_get_charptr(e, SLAPI_USERPWD_ATTR);
    if (!userpw) {
	/* nothing interesting here */
	return 0;
    }

    /* Ok this is interesting,
     * Check this is a clear text password, or refuse operation */
    if ('{' == userpw[0]) {
        if (0 == strncasecmp(userpw, "{CLEAR}", strlen("{CLEAR}"))) {
            char *tmp = slapi_ch_strdup(&userpw[strlen("{CLEAR}")]);
            if (NULL == tmp) {
                slapi_log_error(SLAPI_LOG_FATAL, IPAPWD_PLUGIN_NAME,
                                "Strdup failed, Out of memory\n");
                rc = LDAP_OPERATIONS_ERROR;
                goto done;
            }
            slapi_ch_free_string(&userpw);
            userpw = tmp;
        } else if (slapi_is_encoded(userpw)) {
            /* check if we have access to the unhashed user password */
            char *userpw_clear =
                slapi_entry_attr_get_charptr(e, "unhashed#user#password");

            /* unhashed#user#password doesn't always contain the clear text
             * password, therefore we need to check if its value isn't the same
             * as userPassword to make sure */
            if (!userpw_clear || (0 == strcmp(userpw, userpw_clear))) {
                rc = LDAP_CONSTRAINT_VIOLATION;
                slapi_ch_free_string(&userpw);
            } else {
                userpw = slapi_ch_strdup(userpw_clear);
            }

            slapi_ch_free_string(&userpw_clear);

            if (rc != LDAP_SUCCESS) {
                /* we don't have access to the clear text password;
                 * let it slide if migration is enabled, but don't
                 * generate kerberos keys */
                char *enabled = ipapwd_getIpaConfigAttr("ipamigrationenabled");
                if (NULL == enabled) {
                    slapi_log_error(SLAPI_LOG_PLUGIN, IPAPWD_PLUGIN_NAME,
                                    "no ipaMigrationEnabled in config;"
                                    " assuming FALSE\n");
                } else if (0 == strcmp(enabled, "TRUE")) {
                    return 0;
                }

                slapi_log_error(SLAPI_LOG_PLUGIN, IPAPWD_PLUGIN_NAME,
                                "pre-hashed passwords are not valid\n");
                errMesg = "pre-hashed passwords are not valid\n";
                goto done;
            }
        }
    }

    rc = ipapwd_entry_checks(pb, e,
                             &is_root, &is_krb, &is_smb,
                             NULL, SLAPI_ACL_ADD);
    if (rc != LDAP_SUCCESS) {
        goto done;
    }

    rc = ipapwd_gen_checks(pb, &errMesg, &krbcfg, IPAPWD_CHECK_DN);
    if (rc != LDAP_SUCCESS) {
        goto done;
    }

    /* Get target DN */
    ret = slapi_pblock_get(pb, SLAPI_TARGET_DN, &dn);
    if (ret) {
        rc = LDAP_OPERATIONS_ERROR;
        goto done;
    }

    /* time to get the operation handler */
    ret = slapi_pblock_get(pb, SLAPI_OPERATION, &op);
    if (ret != 0) {
        slapi_log_error(SLAPI_LOG_FATAL, IPAPWD_PLUGIN_NAME,
                        "slapi_pblock_get failed!?\n");
        rc = LDAP_OPERATIONS_ERROR;
        goto done;
    }

    pwdop = slapi_get_object_extension(ipapwd_op_ext_list.object_type,
                                       op, ipapwd_op_ext_list.handle);
    if (NULL == pwdop) {
        rc = LDAP_OPERATIONS_ERROR;
        goto done;
    }

    pwdop->pwd_op = IPAPWD_OP_ADD;
    pwdop->pwdata.password = slapi_ch_strdup(userpw);

    if (is_root) {
        pwdop->pwdata.changetype = IPA_CHANGETYPE_DSMGR;
    } else {
        char *binddn;
        int i;

        pwdop->pwdata.changetype = IPA_CHANGETYPE_ADMIN;

        /* Check Bind DN */
        slapi_pblock_get(pb, SLAPI_CONN_DN, &binddn);

        /* if it is a passsync manager we also need to skip resets */
        for (i = 0; i < krbcfg->num_passsync_mgrs; i++) {
            if (strcasecmp(krbcfg->passsync_mgrs[i], binddn) == 0) {
                pwdop->pwdata.changetype = IPA_CHANGETYPE_DSMGR;
                break;
            }
        }
    }

    pwdop->pwdata.dn = slapi_ch_strdup(dn);
    pwdop->pwdata.timeNow = time(NULL);
    pwdop->pwdata.target = e;

    ret = ipapwd_CheckPolicy(&pwdop->pwdata);
    if (ret) {
        errMesg = "Password Fails to meet minimum strength criteria";
        rc = LDAP_CONSTRAINT_VIOLATION;
        goto done;
    }

    if (is_krb || is_smb) {

        Slapi_Value **svals = NULL;
        char *nt = NULL;
        char *lm = NULL;

        pwdop->is_krb = is_krb;

        rc = ipapwd_gen_hashes(krbcfg, &pwdop->pwdata,
                               userpw, is_krb, is_smb,
                               &svals, &nt, &lm, &errMesg);
        if (rc != LDAP_SUCCESS) {
            goto done;
        }

        if (svals) {
            /* add/replace values in existing entry */
            ret = slapi_entry_attr_replace_sv(e, "krbPrincipalKey", svals);
            if (ret) {
                slapi_log_error(SLAPI_LOG_FATAL, IPAPWD_PLUGIN_NAME,
                                "failed to set encoded values in entry\n");
                rc = LDAP_OPERATIONS_ERROR;
                ipapwd_free_slapi_value_array(&svals);
                goto done;
            }

            ipapwd_free_slapi_value_array(&svals);
        }

        if (lm) {
            /* set value */
            slapi_entry_attr_set_charptr(e, "sambaLMPassword", lm);
            slapi_ch_free_string(&lm);
        }
        if (nt) {
            /* set value */
            slapi_entry_attr_set_charptr(e, "sambaNTPassword", nt);
            slapi_ch_free_string(&nt);
        }
    }

    rc = LDAP_SUCCESS;

done:
    if (pwdop) pwdop->pwdata.target = NULL;
    free_ipapwd_krbcfg(&krbcfg);
    slapi_ch_free_string(&userpw);
    if (rc != LDAP_SUCCESS) {
        slapi_send_ldap_result(pb, rc, NULL, errMesg, 0, NULL);
        return -1;
    }
    return 0;
}

/* PRE MOD Operation:
 * Gets the clean text password (fail the operation if the password came
 * pre-hashed, unless this is a replicated operation).
 * Check user is authorized to add it otherwise just returns, operation will
 * fail later anyway.
 * Check if krb or smb hashes are required by testing if the krb or smb
 * objectclasses are present.
 * Run a password policy check.
 * store information for the post operation
 */
static int ipapwd_pre_mod(Slapi_PBlock *pb)
{
    struct ipapwd_krbcfg *krbcfg = NULL;
    char *errMesg = NULL;
    LDAPMod **mods;
    Slapi_Mod *smod, *tmod;
    Slapi_Mods *smods = NULL;
    char *userpw = NULL;
    char *unhashedpw = NULL;
    char *dn = NULL;
    Slapi_DN *tmp_dn;
    struct slapi_entry *e = NULL;
    struct ipapwd_operation *pwdop = NULL;
    void *op;
    int is_repl_op, is_pwd_op, is_root, is_krb, is_smb;
    int ret, rc;

    slapi_log_error(SLAPI_LOG_TRACE, IPAPWD_PLUGIN_NAME, "=> ipapwd_pre_mod\n");

    ret = slapi_pblock_get(pb, SLAPI_IS_REPLICATED_OPERATION, &is_repl_op);
    if (ret != 0) {
        slapi_log_error(SLAPI_LOG_FATAL, IPAPWD_PLUGIN_NAME,
                        "slapi_pblock_get failed!?\n");
        rc = LDAP_OPERATIONS_ERROR;
        goto done;
    }

    /* pass through if this is a replicated operation */
    if (is_repl_op) {
        rc = LDAP_SUCCESS;
        goto done;
    }

    /* grab the mods - we'll put them back later with
     * our modifications appended
     */
    slapi_pblock_get(pb, SLAPI_MODIFY_MODS, &mods);
    smods = slapi_mods_new();
    slapi_mods_init_passin(smods, mods);

    /* In the first pass,
     * only check there is anything we are interested in */
    is_pwd_op = 0;
    tmod = slapi_mod_new();
    smod = slapi_mods_get_first_smod(smods, tmod);
    while (smod) {
        struct berval *bv;
        const char *type;
        int mop;

        type = slapi_mod_get_type(smod);
        if (slapi_attr_types_equivalent(type, SLAPI_USERPWD_ATTR)) {
            mop = slapi_mod_get_operation(smod);
            /* check op filtering out LDAP_MOD_BVALUES */
            switch (mop & 0x0f) {
            case LDAP_MOD_ADD:
            case LDAP_MOD_REPLACE:
                is_pwd_op = 1;
            default:
                break;
            }
        }

        /* we check for unahsehd password here so that we are sure to catch them
         * early, before further checks go on, this helps checking
         * LDAP_MOD_DELETE operations in some corner cases later */
        /* we keep only the last one if multiple are provided for any absurd
	 * reason */
        if (slapi_attr_types_equivalent(type, "unhashed#user#password")) {
            bv = slapi_mod_get_first_value(smod);
            if (!bv) {
                slapi_mod_free(&tmod);
                rc = LDAP_OPERATIONS_ERROR;
                goto done;
            }
            slapi_ch_free_string(&unhashedpw);
            unhashedpw = slapi_ch_malloc(bv->bv_len+1);
            if (!unhashedpw) {
                slapi_mod_free(&tmod);
                rc = LDAP_OPERATIONS_ERROR;
                goto done;
            }
            memcpy(unhashedpw, bv->bv_val, bv->bv_len);
            unhashedpw[bv->bv_len] = '\0';
        }
        slapi_mod_done(tmod);
        smod = slapi_mods_get_next_smod(smods, tmod);
    }
    slapi_mod_free(&tmod);

    /* If userPassword is not modified we are done here */
    if (! is_pwd_op) {
        rc = LDAP_SUCCESS;
        goto done;
    }

    /* OK swe have something interesting here, start checking for
     * pre-requisites */

    /* Get target DN */
    ret = slapi_pblock_get(pb, SLAPI_TARGET_DN, &dn);
    if (ret) {
        rc = LDAP_OPERATIONS_ERROR;
        goto done;
    }

    tmp_dn = slapi_sdn_new_dn_byref(dn);
    if (tmp_dn) {
        /* xxxPAR: Ideally SLAPI_MODIFY_EXISTING_ENTRY should be
         * available but it turns out that is only true if you are
         * a dbm backend pre-op plugin - lucky dbm backend pre-op
         * plugins.
         * I think that is wrong since the entry is useful for filter
         * tests and schema checks and this plugin shouldn't be limited
         * to a single backend type, but I don't want that fight right
         * now so we go get the entry here
         *
         slapi_pblock_get( pb, SLAPI_MODIFY_EXISTING_ENTRY, &e);
         */
        ret = slapi_search_internal_get_entry(tmp_dn, 0, &e, ipapwd_plugin_id);
        slapi_sdn_free(&tmp_dn);
        if (ret != LDAP_SUCCESS) {
            slapi_log_error(SLAPI_LOG_PLUGIN, IPAPWD_PLUGIN_NAME,
                            "Failed tpo retrieve entry?!?\n");
           rc = LDAP_NO_SUCH_OBJECT;
           goto done;
        }
    }

    rc = ipapwd_entry_checks(pb, e,
                             &is_root, &is_krb, &is_smb,
                             SLAPI_USERPWD_ATTR, SLAPI_ACL_WRITE);
    if (rc) {
        goto done;
    }

    rc = ipapwd_gen_checks(pb, &errMesg, &krbcfg, IPAPWD_CHECK_DN);
    if (rc) {
        goto done;
    }

    /* run through the mods again and adjust flags if operations affect them */
    tmod = slapi_mod_new();
    smod = slapi_mods_get_first_smod(smods, tmod);
    while (smod) {
        struct berval *bv;
        const char *type;
        int mop;

        type = slapi_mod_get_type(smod);
        if (slapi_attr_types_equivalent(type, SLAPI_USERPWD_ATTR)) {
            mop = slapi_mod_get_operation(smod);
            /* check op filtering out LDAP_MOD_BVALUES */
            switch (mop & 0x0f) {
            case LDAP_MOD_ADD:
                /* FIXME: should we try to track cases where we would end up
                 * with multiple userPassword entries ?? */
            case LDAP_MOD_REPLACE:
                is_pwd_op = 1;
                bv = slapi_mod_get_first_value(smod);
                if (!bv) {
                    slapi_mod_free(&tmod);
                    rc = LDAP_OPERATIONS_ERROR;
                    goto done;
                }
                slapi_ch_free_string(&userpw);
                userpw = slapi_ch_malloc(bv->bv_len+1);
                if (!userpw) {
                    slapi_mod_free(&tmod);
                    rc = LDAP_OPERATIONS_ERROR;
                    goto done;
                }
                memcpy(userpw, bv->bv_val, bv->bv_len);
                userpw[bv->bv_len] = '\0';
                break;
            case LDAP_MOD_DELETE:
                /* reset only if we are deleting all values, or the exact
                 * same value previously set, otherwise we are just trying to
                 * add a new value and delete an existing one */
                bv = slapi_mod_get_first_value(smod);
                if (!bv) {
                    is_pwd_op = 0;
                } else {
                    if (0 == strncmp(userpw, bv->bv_val, bv->bv_len) ||
                        0 == strncmp(unhashedpw, bv->bv_val, bv->bv_len))
                        is_pwd_op = 0;
                }
            default:
                break;
            }
        }

        if (slapi_attr_types_equivalent(type, SLAPI_ATTR_OBJECTCLASS)) {
            mop = slapi_mod_get_operation(smod);
            /* check op filtering out LDAP_MOD_BVALUES */
            switch (mop & 0x0f) {
            case LDAP_MOD_REPLACE:
                /* if objectclasses are replaced we need to start clean with
                 * flags, so we sero them out and see if they get set again */
                is_krb = 0;
                is_smb = 0;

            case LDAP_MOD_ADD:
                bv = slapi_mod_get_first_value(smod);
                if (!bv) {
                    slapi_mod_free(&tmod);
                    rc = LDAP_OPERATIONS_ERROR;
                    goto done;
                }
                do {
                    if (0 == strncasecmp("krbPrincipalAux", bv->bv_val, bv->bv_len))
                        is_krb = 1;
                    if (0 == strncasecmp("sambaSamAccount", bv->bv_val, bv->bv_len))
                        is_smb = 1;
                } while ((bv = slapi_mod_get_next_value(smod)) != NULL);

                break;

            case LDAP_MOD_DELETE:
                /* can this happen for objectclasses ? */
                is_krb = 0;
                is_smb = 0;

            default:
                break;
            }
        }

        slapi_mod_done(tmod);
        smod = slapi_mods_get_next_smod(smods, tmod);
    }
    slapi_mod_free(&tmod);

    /* It seem like we have determined that the end result will be deletion of
     * the userPassword attribute, so we have no more business here */
    if (! is_pwd_op) {
        rc = LDAP_SUCCESS;
        goto done;
    }

    /* Check this is a clear text password, or refuse operation (only if we need
     * to comput other hashes */
    if (! unhashedpw) {
        if ('{' == userpw[0]) {
            if (0 == strncasecmp(userpw, "{CLEAR}", strlen("{CLEAR}"))) {
                unhashedpw = slapi_ch_strdup(&userpw[strlen("{CLEAR}")]);
                if (NULL == unhashedpw) {
                    slapi_log_error(SLAPI_LOG_FATAL, IPAPWD_PLUGIN_NAME,
                                    "Strdup failed, Out of memory\n");
                    rc = LDAP_OPERATIONS_ERROR;
                    goto done;
                }
                slapi_ch_free_string(&userpw);

            } else if (slapi_is_encoded(userpw)) {

                slapi_log_error(SLAPI_LOG_PLUGIN, IPAPWD_PLUGIN_NAME,
                                "Pre-Encoded passwords are not valid\n");
                errMesg = "Pre-Encoded passwords are not valid\n";
                rc = LDAP_CONSTRAINT_VIOLATION;
                goto done;
            }
        }
    }

    /* time to get the operation handler */
    ret = slapi_pblock_get(pb, SLAPI_OPERATION, &op);
    if (ret != 0) {
        slapi_log_error(SLAPI_LOG_FATAL, IPAPWD_PLUGIN_NAME,
                        "slapi_pblock_get failed!?\n");
        rc = LDAP_OPERATIONS_ERROR;
        goto done;
    }

    pwdop = slapi_get_object_extension(ipapwd_op_ext_list.object_type,
                                       op, ipapwd_op_ext_list.handle);
    if (NULL == pwdop) {
        rc = LDAP_OPERATIONS_ERROR;
        goto done;
    }

    pwdop->pwd_op = IPAPWD_OP_MOD;
    pwdop->pwdata.password = slapi_ch_strdup(unhashedpw);
    pwdop->pwdata.changetype = IPA_CHANGETYPE_NORMAL;

    if (is_root) {
        pwdop->pwdata.changetype = IPA_CHANGETYPE_DSMGR;
    } else {
        char *binddn;
        Slapi_DN *bdn, *tdn;
        int i;

        /* Check Bind DN */
        slapi_pblock_get(pb, SLAPI_CONN_DN, &binddn);
        bdn = slapi_sdn_new_dn_byref(binddn);
        tdn = slapi_sdn_new_dn_byref(dn);

        /* if the change is performed by someone else,
         * it is an admin change that will require a new
         * password change immediately as per our IPA policy */
        if (slapi_sdn_compare(bdn, tdn)) {
            pwdop->pwdata.changetype = IPA_CHANGETYPE_ADMIN;

            /* if it is a passsync manager we also need to skip resets */
            for (i = 0; i < krbcfg->num_passsync_mgrs; i++) {
                if (strcasecmp(krbcfg->passsync_mgrs[i], binddn) == 0) {
                    pwdop->pwdata.changetype = IPA_CHANGETYPE_DSMGR;
                    break;
                }
            }

        }

        slapi_sdn_free(&bdn);
        slapi_sdn_free(&tdn);

    }

    pwdop->pwdata.dn = slapi_ch_strdup(dn);
    pwdop->pwdata.timeNow = time(NULL);
    pwdop->pwdata.target = e;

    ret = ipapwd_CheckPolicy(&pwdop->pwdata);
    if (ret) {
        errMesg = "Password Fails to meet minimum strength criteria";
        rc = LDAP_CONSTRAINT_VIOLATION;
        goto done;
    }

    if (is_krb || is_smb) {

        Slapi_Value **svals = NULL;
        char *nt = NULL;
        char *lm = NULL;

        rc = ipapwd_gen_hashes(krbcfg, &pwdop->pwdata, unhashedpw,
                               is_krb, is_smb, &svals, &nt, &lm, &errMesg);
        if (rc) {
            goto done;
        }

        if (svals) {
            /* replace values */
            slapi_mods_add_mod_values(smods, LDAP_MOD_REPLACE,
                                      "krbPrincipalKey", svals);
            ipapwd_free_slapi_value_array(&svals);
        }

        if (lm) {
            /* replace value */
            slapi_mods_add_string(smods, LDAP_MOD_REPLACE,
                                  "sambaLMPassword", lm);
            slapi_ch_free_string(&lm);
        }
        if (nt) {
            /* replace value */
            slapi_mods_add_string(smods, LDAP_MOD_REPLACE,
                                  "sambaNTPassword", nt);
            slapi_ch_free_string(&nt);
        }
    }

    rc = LDAP_SUCCESS;

done:
    free_ipapwd_krbcfg(&krbcfg);
    slapi_ch_free_string(&userpw); /* just to be sure */
    slapi_ch_free_string(&unhashedpw); /* we copied it to pwdop  */
    if (e) slapi_entry_free(e); /* this is a copy in this function */
    if (pwdop) pwdop->pwdata.target = NULL;

    /* put back a, possibly modified, set of mods */
    if (smods) {
        mods = slapi_mods_get_ldapmods_passout(smods);
        slapi_pblock_set(pb, SLAPI_MODIFY_MODS, mods);
        slapi_mods_free(&smods);
    }

    if (rc != LDAP_SUCCESS) {
        slapi_send_ldap_result(pb, rc, NULL, errMesg, 0, NULL);
        return -1;
    }

    return 0;
}

static int ipapwd_post_op(Slapi_PBlock *pb)
{
    void *op;
    struct ipapwd_operation *pwdop = NULL;
    Slapi_Mods *smods;
    Slapi_Value **pwvals;
    struct tm utctime;
    char timestr[GENERALIZED_TIME_LENGTH+1];
    int ret;

    slapi_log_error(SLAPI_LOG_TRACE, IPAPWD_PLUGIN_NAME,
                    "=> ipapwd_post_op\n");

    /* time to get the operation handler */
    ret = slapi_pblock_get(pb, SLAPI_OPERATION, &op);
    if (ret != 0) {
        slapi_log_error(SLAPI_LOG_FATAL, IPAPWD_PLUGIN_NAME,
                        "slapi_pblock_get failed!?\n");
        return 0;
    }

    pwdop = slapi_get_object_extension(ipapwd_op_ext_list.object_type,
                                       op, ipapwd_op_ext_list.handle);
    if (NULL == pwdop) {
        slapi_log_error(SLAPI_LOG_PLUGIN, IPAPWD_PLUGIN_NAME,
                        "Internal error, couldn't find pluginextension ?!\n");
        return 0;
    }

    /* not interesting */
    if (IPAPWD_OP_NULL == pwdop->pwd_op)
        return 0;

    if ( ! (pwdop->is_krb)) {
        slapi_log_error(SLAPI_LOG_PLUGIN, IPAPWD_PLUGIN_NAME,
                        "Not a kerberos user, ignore krb attributes\n");
        return 0;
    }

    /* prepare changes that can be made only as root */
    smods = slapi_mods_new();

    /* change Last Password Change field with the current date */
    if (!gmtime_r(&(pwdop->pwdata.timeNow), &utctime)) {
        slapi_log_error(SLAPI_LOG_PLUGIN, IPAPWD_PLUGIN_NAME,
                        "failed to parse current date (buggy gmtime_r ?)\n");
        goto done;
    }
    strftime(timestr, GENERALIZED_TIME_LENGTH+1,
             "%Y%m%d%H%M%SZ", &utctime);
    slapi_mods_add_string(smods, LDAP_MOD_REPLACE,
                          "krbLastPwdChange", timestr);

    /* set Password Expiration date */
    if (!gmtime_r(&(pwdop->pwdata.expireTime), &utctime)) {
        slapi_log_error(SLAPI_LOG_PLUGIN, IPAPWD_PLUGIN_NAME,
                        "failed to parse expiration date (buggy gmtime_r ?)\n");
        goto done;
    }
    strftime(timestr, GENERALIZED_TIME_LENGTH+1,
             "%Y%m%d%H%M%SZ", &utctime);
    slapi_mods_add_string(smods, LDAP_MOD_REPLACE,
                          "krbPasswordExpiration", timestr);

    /* This was a mod operation on an existing entry, make sure we also update
     * the password history based on the entry we saved from the pre-op */
    if (IPAPWD_OP_MOD == pwdop->pwd_op) {
        Slapi_DN *tmp_dn = slapi_sdn_new_dn_byref(pwdop->pwdata.dn);
        if (tmp_dn) {
            ret = slapi_search_internal_get_entry(tmp_dn, 0,
                                                  &pwdop->pwdata.target,
                                                  ipapwd_plugin_id);
            slapi_sdn_free(&tmp_dn);
            if (ret != LDAP_SUCCESS) {
                slapi_log_error(SLAPI_LOG_PLUGIN, IPAPWD_PLUGIN_NAME,
                                "Failed tpo retrieve entry?!?\n");
                goto done;
            }
        }
        pwvals = ipapwd_setPasswordHistory(smods, &pwdop->pwdata);
        if (pwvals) {
            slapi_mods_add_mod_values(smods, LDAP_MOD_REPLACE,
                                      "passwordHistory", pwvals);
        }
    }

    ret = ipapwd_apply_mods(pwdop->pwdata.dn, smods);
    if (ret)
        slapi_log_error(SLAPI_LOG_PLUGIN, IPAPWD_PLUGIN_NAME,
           "Failed to set additional password attributes in the post-op!\n");

done:
    if (pwdop && pwdop->pwdata.target) slapi_entry_free(pwdop->pwdata.target);
    slapi_mods_free(&smods);
    return 0;
}

/* PRE BIND Operation:
 * Used for password migration from DS to IPA.
 * Gets the clean text password, authenticates the user and generates
 * a kerberos key if missing.
 * Person to blame if anything blows up: Pavel Zuna <pzuna@redhat.com>
 */
static int ipapwd_pre_bind(Slapi_PBlock *pb)
{
    struct ipapwd_krbcfg *krbcfg = NULL;
    struct ipapwd_data pwdata;
    struct berval *credentials; /* bind credentials */
    Slapi_Entry *entry = NULL;
    Slapi_Value **pwd_values = NULL; /* values of userPassword attribute */
    Slapi_Value *value = NULL;
    Slapi_Attr *attr = NULL;
    struct tm expire_tm;
    time_t expire_time;
    char *errMesg = "Internal operations error\n"; /* error message */
    char *expire = NULL; /* passwordExpirationTime attribute value */
    char *dn = NULL; /* bind DN */
    Slapi_Value *objectclass;
    int method; /* authentication method */
    int ret = 0;

    slapi_log_error(SLAPI_LOG_TRACE, IPAPWD_PLUGIN_NAME,
                    "=> ipapwd_pre_bind\n");

    /* get BIND parameters */
    ret |= slapi_pblock_get(pb, SLAPI_BIND_TARGET, &dn);
    ret |= slapi_pblock_get(pb, SLAPI_BIND_METHOD, &method);
    ret |= slapi_pblock_get(pb, SLAPI_BIND_CREDENTIALS, &credentials);
    if (ret) {
        slapi_log_error(SLAPI_LOG_FATAL, "ipapwd_pre_bind",
                        "slapi_pblock_get failed!?\n");
        goto done;
    }

    /* we're only interested in simple authentication */
    if (method != LDAP_AUTH_SIMPLE)
        goto done;

    /* list of attributes to retrieve */
    const char *attrs_list[] = {SLAPI_USERPWD_ATTR, "krbprincipalkey", "uid",
                                "krbprincipalname", "objectclass",
                                "passwordexpirationtime",  "passwordhistory",
                                NULL};

    /* retrieve user entry */
    ret = ipapwd_getEntry(dn, &entry, (char **) attrs_list);
    if (ret) {
        slapi_log_error(SLAPI_LOG_PLUGIN, "ipapwd_pre_bind",
                        "failed to retrieve user entry: %s\n", dn);
        goto done;
    }

    /* check the krbPrincipalName attribute is present */
    ret = slapi_entry_attr_find(entry, "krbprincipalname", &attr);
    if (ret) {
        slapi_log_error(SLAPI_LOG_PLUGIN, "ipapwd_pre_bind",
                        "no krbPrincipalName in user entry: %s\n", dn);
        goto done;
    }

    /* we aren't interested in host principals */
    objectclass = slapi_value_new_string("ipaHost");
    if ((slapi_entry_attr_has_syntax_value(entry, SLAPI_ATTR_OBJECTCLASS, objectclass)) == 1) {
        slapi_value_free(&objectclass);
        goto done;
    }
    slapi_value_free(&objectclass);

    /* check the krbPrincipalKey attribute is NOT present */
    ret = slapi_entry_attr_find(entry, "krbprincipalkey", &attr);
    if (!ret) {
        slapi_log_error(SLAPI_LOG_PLUGIN, "ipapwd_pre_bind",
                        "kerberos key already present in user entry: %s\n", dn);
        goto done;
    }

    /* retrieve userPassword attribute */
    ret = slapi_entry_attr_find(entry, SLAPI_USERPWD_ATTR, &attr);
    if (ret) {
        slapi_log_error(SLAPI_LOG_PLUGIN, "ipapwd_pre_bind",
                        "no " SLAPI_USERPWD_ATTR " in user entry: %s\n", dn);
        goto done;
    }

    /* get the number of userPassword values and allocate enough memory */
    slapi_attr_get_numvalues(attr, &ret);
    ret = (ret + 1) * sizeof (Slapi_Value *);
    pwd_values = (Slapi_Value **) slapi_ch_malloc(ret);
    if (!pwd_values) {
        /* probably not required: should terminate the server anyway */
        slapi_log_error(SLAPI_LOG_FATAL, IPAPWD_PLUGIN_NAME,
                        "out of memory!?\n");
        goto done;
    }
    /* zero-fill the allocated memory; we need the array ending with NULL */
    memset(pwd_values, 0, ret);

    /* retrieve userPassword values */
    ret = slapi_attr_first_value(attr, &value);
    while (ret != -1) {
        pwd_values[ret] = value;
        ret = slapi_attr_next_value(attr, ret, &value);
    }

    /* check if BIND password and userPassword match */
    value = slapi_value_new_berval(credentials);
    ret = slapi_pw_find_sv(pwd_values, value);

    /* free before checking ret; we might not get a chance later */
    slapi_ch_free((void **) &pwd_values);
    slapi_value_free(&value);

    if (ret) {
        slapi_log_error(SLAPI_LOG_PLUGIN, "ipapwd_pre_bind",
                        "invalid BIND password for user entry: %s\n", dn);
        goto done;
    }

    /* general checks */
    ret = ipapwd_gen_checks(pb, &errMesg, &krbcfg, IPAPWD_CHECK_DN);
    if (ret) {
        slapi_log_error(SLAPI_LOG_FATAL, "ipapwd_pre_bind",
                        "ipapwd_gen_checks failed: %s", errMesg);
        goto done;
    }

    /* delete userPassword - a new one will be generated later */
    /* this is needed, otherwise ipapwd_CheckPolicy will think
     * we're changing the password to its previous value
     * and force a password change on next login  */
    ret = slapi_entry_attr_delete(entry, SLAPI_USERPWD_ATTR);
    if (ret) {
        slapi_log_error(SLAPI_LOG_PLUGIN, "ipapwd_pre_bind",
                        "failed to delete " SLAPI_USERPWD_ATTR "\n");
        goto done;
    }

    /* prepare data for kerberos key generation */
    memset(&pwdata, 0, sizeof (pwdata));
    pwdata.dn = dn;
    pwdata.target = entry;
    pwdata.password = credentials->bv_val;
    pwdata.timeNow = time(NULL);
    pwdata.changetype = IPA_CHANGETYPE_NORMAL;

    /* keep password expiration time from DS, if possible */
    expire = slapi_entry_attr_get_charptr(entry, "passwordexpirationtime");
    if (expire) {
        memset(&expire_tm, 0, sizeof (expire_tm));
        if (strptime(expire, "%Y%m%d%H%M%SZ", &expire_tm))
            pwdata.expireTime = mktime(&expire_tm);
    }

    /* check password policy */
    ret = ipapwd_CheckPolicy(&pwdata);
    if (ret) {
        /* Password fails to meet IPA password policy,
         * force user to change his password next time he logs in. */
        slapi_log_error(SLAPI_LOG_PLUGIN, "ipapwd_pre_bind",
                        "password policy check failed on user entry: %s"
                        " (force password change on next login)\n", dn);
        pwdata.expireTime = time(NULL);
    }

    /* generate kerberos keys */
    ret = ipapwd_SetPassword(krbcfg, &pwdata, 1);
    if (ret) {
        slapi_log_error(SLAPI_LOG_PLUGIN, "ipapwd_pre_bind",
                        "failed to set kerberos key for user entry: %s\n", dn);
        goto done;
    }

    slapi_log_error(SLAPI_LOG_PLUGIN, "ipapwd_pre_bind",
                    "kerberos key generated for user entry: %s\n", dn);

done:
    slapi_ch_free_string(&expire);
    if (entry)
        slapi_entry_free(entry);
    free_ipapwd_krbcfg(&krbcfg);

    return 0;
}



/* Init pre ops */
int ipapwd_pre_init(Slapi_PBlock *pb)
{
    int ret;

    ret = slapi_pblock_set(pb, SLAPI_PLUGIN_VERSION, SLAPI_PLUGIN_VERSION_01);
    if (!ret) ret = slapi_pblock_set(pb, SLAPI_PLUGIN_DESCRIPTION, (void *)&ipapwd_plugin_desc);
    if (!ret) ret = slapi_pblock_set(pb, SLAPI_PLUGIN_PRE_BIND_FN, (void *)ipapwd_pre_bind);
    if (!ret) ret = slapi_pblock_set(pb, SLAPI_PLUGIN_PRE_ADD_FN, (void *)ipapwd_pre_add);
    if (!ret) ret = slapi_pblock_set(pb, SLAPI_PLUGIN_PRE_MODIFY_FN, (void *)ipapwd_pre_mod);

    return ret;
}

/* Init post ops */
int ipapwd_post_init(Slapi_PBlock *pb)
{
    int ret;

    ret = slapi_pblock_set(pb, SLAPI_PLUGIN_VERSION, SLAPI_PLUGIN_VERSION_01);
    if (!ret) ret = slapi_pblock_set(pb, SLAPI_PLUGIN_DESCRIPTION, (void *)&ipapwd_plugin_desc);
    if (!ret) ret = slapi_pblock_set(pb, SLAPI_PLUGIN_POST_ADD_FN, (void *)ipapwd_post_op);
    if (!ret) ret = slapi_pblock_set(pb, SLAPI_PLUGIN_POST_MODIFY_FN, (void *)ipapwd_post_op);

    return ret;
}
