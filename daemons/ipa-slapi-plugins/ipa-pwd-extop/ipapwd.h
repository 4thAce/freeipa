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

#include <prio.h>
#include <ssl.h>
#include <dirsrv/slapi-plugin.h>
#define KRB5_PRIVATE 1
#include <krb5.h>
#include <lber.h>
#include <time.h>
#include <iconv.h>
#include <openssl/des.h>
#include <openssl/md4.h>

#define IPAPWD_PLUGIN_NAME   "ipa-pwd-extop"
#define IPAPWD_FEATURE_DESC  "IPA Password Manager"
#define IPAPWD_PLUGIN_DESC   "IPA Password Extended Operation plugin"

#define IPAPWD_CHECK_CONN_SECURE    0x00000001
#define IPAPWD_CHECK_DN             0x00000002

#define IPA_CHANGETYPE_NORMAL 0
#define IPA_CHANGETYPE_ADMIN 1
#define IPA_CHANGETYPE_DSMGR 2

struct ipapwd_data {
    Slapi_Entry *target;
    char *dn;
    char *password;
    time_t timeNow;
    time_t lastPwChange;
    time_t expireTime;
    int changetype;
    int pwHistoryLen;
};

struct ipapwd_operation {
    struct ipapwd_data pwdata;
    int pwd_op;
    int is_krb;
};

#define GENERALIZED_TIME_LENGTH 15

#define IPAPWD_POLICY_MASK 0x0FF
#define IPAPWD_POLICY_ERROR 0x100
#define IPAPWD_POLICY_OK 0


/* from ipapwd_common.c */
struct ipapwd_encsalt {
    krb5_int32 enc_type;
    krb5_int32 salt_type;
};

struct ipapwd_krbcfg {
    krb5_context krbctx;
    char *realm;
    krb5_keyblock *kmkey;
    int num_supp_encsalts;
    struct ipapwd_encsalt *supp_encsalts;
    int num_pref_encsalts;
    struct ipapwd_encsalt *pref_encsalts;
    char **passsync_mgrs;
    int num_passsync_mgrs;
};

int ipapwd_entry_checks(Slapi_PBlock *pb, struct slapi_entry *e,
                        int *is_root, int *is_krb, int *is_smb,
                        char *attr, int access);
int ipapwd_gen_checks(Slapi_PBlock *pb, char **errMesg,
                      struct ipapwd_krbcfg **config, int check_flags);
int ipapwd_CheckPolicy(struct ipapwd_data *data);
int ipapwd_getEntry(const char *dn, Slapi_Entry **e2, char **attrlist);
int ipapwd_get_cur_kvno(Slapi_Entry *target);
int ipapwd_SetPassword(struct ipapwd_krbcfg *krbcfg,
                       struct ipapwd_data *data, int is_krb);
Slapi_Value **ipapwd_setPasswordHistory(Slapi_Mods *smods,
                                        struct ipapwd_data *data);
int ipapwd_apply_mods(const char *dn, Slapi_Mods *mods);
void ipapwd_free_slapi_value_array(Slapi_Value ***svals);
void free_ipapwd_krbcfg(struct ipapwd_krbcfg **cfg);

/* from ipapwd_encoding.c */
struct ipapwd_krbkeydata {
    int32_t type;
    struct berval value;
};
struct ipapwd_krbkey {
    struct ipapwd_krbkeydata *salt;
    struct ipapwd_krbkeydata *ekey;
    struct berval s2kparams;
};
struct ipapwd_keyset {
    uint16_t major_vno;
    uint16_t minor_vno;
    uint32_t kvno;
    uint32_t mkvno;
    struct ipapwd_krbkey *keys;
    int num_keys;
};

struct berval *encode_keys(struct ipapwd_keyset *kset);
void ipapwd_keyset_free(struct ipapwd_keyset **pkset);

int ipapwd_gen_hashes(struct ipapwd_krbcfg *krbcfg,
                      struct ipapwd_data *data, char *userpw,
                      int is_krb, int is_smb, Slapi_Value ***svals,
                      char **nthash, char **lmhash, char **errMesg);

/* from ipapwd_prepost.c */
int ipapwd_ext_init(void);
int ipapwd_pre_init(Slapi_PBlock *pb);
int ipapwd_post_init(Slapi_PBlock *pb);
