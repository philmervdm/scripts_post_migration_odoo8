#!/usr/bin/python
#-*- coding: utf-8 -*-

import xmlrpclib
import os
import csv
import psycopg2
import sys

execfile('params.txt')

def lower_wo_accent(name):
    good_name = name.lower().replace (u'é','e').replace (u'è','e').replace (u'â','a').replace (u'ê','e')
    if len(good_name) > 2 and (good_name[-2:] == ' 1' or good_name[-2:] == ' 2'):
        good_name = good_name[:-2]
    return good_name
FIRST_STEP = 12
LAST_STEP = 12

url = 'http://%s/xmlrpc' % connect['url']
sock_obj = xmlrpclib.ServerProxy(url+'/object')
sock_connect = xmlrpclib.ServerProxy(url+'/common')

admin_login = connect['admin_login']
admin_passwd = connect['admin_passwd']
dbname = connect['dbname']
psql_server = connect['pserver']
psql_user = connect['puser']
psql_pw = connect['ppassword']

#dbname = 'test_addr' # to force the database name 

uid = sock_connect.login(dbname, admin_login, admin_passwd)
print "UID : " + str(uid)

conn = psycopg2.connect(database=dbname, user=psql_user, password=psql_pw, host=psql_server)
cur = conn.cursor()

# Ajoute les liens vers les pays dans les codes postaux s'ils peuvent être retrouvés
if FIRST_STEP <= 1 and LAST_STEP >= 1:
    print "### CORRECT ZIPS ##############################"
    country_ids = sock_obj.execute(dbname,uid,admin_passwd, 'res.country', 'search', [] )
    countries = sock_obj.execute(dbname,uid,admin_passwd, 'res.country', 'read', country_ids, ['name','code'] )
    dCountries = {}
    for country in countries:
        if country['code']:
            dCountries[country['code'].upper()] = country['id']
    print dCountries
    print dCountries['BE']
    zip_group_type_ids = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner.zip.group.type', 'search', [('name','=',u'Codes postaux étrangers')] )
    if zip_group_type_ids:
        zip_group_ids = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner.zip.group', 'search', [('type_id','in',zip_group_type_ids)] )
        if zip_group_ids:
            zip_groups = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner.zip.group', 'read', zip_group_ids, ['name'] )
            dZipGroups = {}
            for group in zip_groups:
                dZipGroups[group['id']] = group['name']
            zip_ids = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner.zip', 'search', [] )
            zips = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner.zip', 'read', zip_ids, ['name','code','groups_id','country_id'],{'lang':'fr_FR'})
            for zip_code in zips:
                new_data = {}
                if (not zip_code['code']) and zip_code['name']:
                    new_data['code'] = zip_code['name']
                if not zip_code['country_id']:
                    if zip_code['groups_id']:
                        for group_id in zip_code['groups_id']:
                            if group_id in zip_group_ids:
                                group_name = dZipGroups[group_id]
                                if group_name == 'Belgique':
                                    group_name = 'BE'
                                if group_name == 'GB ou UK':
                                    group_name = 'UK'
                                if group_name == 'Tunisie':
                                    group_name = 'TN'
                                if dCountries.has_key(group_name):
                                    new_data['country_id'] = dCountries[group_name]
                                else:
                                    print 'group name not found : ' +group_name
                if new_data:
                    #print 'new_data'
                    #print new_data
                    if not new_data.has_key('country_id') and zip_code['groups_id']:
                        print zip_code
                        print 'no country found'
                    print sock_obj.execute(dbname,uid,admin_passwd, 'res.partner.zip', 'write', [zip_code['id'],], new_data)
                else:
                    print zip_code
                    print 'no new data'

# Rajoute les status_id sur les fiches partenaires une fois le '--update all' exécuté
if FIRST_STEP <= 2 and LAST_STEP >= 2:
    print "### CORRECT STATUS_ID ##############################"
    if os.path.exists('./res_partner_status.csv'):
        print "Reinject Status_id"
        hfInput = csv.DictReader(open('./res_partner_status.csv','r'),delimiter=";",quotechar='"')
        corrected = 0
        wrong = 0
        for ligne in hfInput:
            try:
                sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', [int(ligne['id']),], {'status_id':int(ligne['status_id'])} )
                corrected += 1
            except Exception, erreur:
                print erreur
                wrong += 1
        print '--------------'
        print 'reinjected : ' + str(corrected)
        print 'wrong ID : ' + str(wrong)
    
# vérification des zip_id sur les partenaires seuls
if FIRST_STEP <= 3 and LAST_STEP >= 3:
    print "### CHECK PARTNER ZIPS ##############################"
    zip_ids = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner.zip', 'search', [] )
    zips = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner.zip', 'read', zip_ids, ['name','code','city','groups_id','country_id'],{'lang':'fr_FR'})
    dZips = {}
    for zip_info in zips:
        dZips[zip_info['id']] = zip_info
    partner_ids = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'search', [('zip_id','!=',False)] )
    partners = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'read', partner_ids, ['name','zip','city','country_id','zip_id','type','is_company'],{'lang':'fr_FR'} )
    count1 = 0
    count2 = 0
    count3 = 0
    count4 = 0
    count5 = 0
    error4 = {}
    for partner in partners:
        zip_info = dZips[partner['zip_id'][0]]
        if zip_info['country_id'] and partner['country_id']:
            if zip_info['name'] == partner['zip'] and zip_info['city'] == partner['city'] and zip_info['country_id'][0] == partner['country_id'][0]:
                #print 'same zip info'
                count1 += 1
            else:
                if ((lower_wo_accent(zip_info['name']) == lower_wo_accent(partner['zip'])) and (lower_wo_accent(zip_info['city']) == lower_wo_accent(partner['city'])) and (zip_info['country_id'][0] == partner['country_id'][0])) or (partner['zip'] == 'manuel'):
                    new_data = {'zip':zip_info['name'],'city':zip_info['city'],'country_id':zip_info['country_id'][0]}
                    sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', [partner['id'],],new_data)
                    count1 += 1
                else:
                    print '----difference between zip and partner info-----'
                    print '- zip:'
                    print zip_info['name']
                    print zip_info['city']
                    print zip_info['country_id']
                    print '- partner:'
                    print partner['zip']
                    print partner['city']
                    print partner['country_id']
                    print partner['type']
                    print partner['is_company']
                    count2 += 1
        else:
            if zip_info['name'] == partner['zip'] and zip_info['city'] == partner['city']:
                #print 'same zip info'
                count3 += 1
            else:
                #print '----difference between zip and partner info-----'
                #if not error4.has_key(partner['type']):
                #    error4[partner['type']] = 1
                #else:
                #    error4[partner['type']] += 1
                if not partner['zip'] and not partner['city']:
                    count5 += 1
                    new_data = {'zip':zip_info['name'],'city':zip_info['city']}
                    if zip_info['country_id']:
                        new_data['country_id'] = zip_info['country_id'][0]
                    sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', [partner['id'],],new_data)
                #print '- zip:'
                #print zip_info['name']
                #print zip_info['city']
                #print '- partner:'
                #print partner['zip']
                #print partner['city']
                #print partner['type']
                #print partner['is_company']
                count4 += 1
    print "1.                        Same ZIP Info " + str(count1)
    print "2. Difference but country is both cases " + str(count2)
    print "3.      Same Zip Info without countries " + str(count3)
    print "4.  Difference in zip without countries " + str(count4)
    print "5.            because empty zip and city" + str(count5)
    print "Cases error4 and 5"
    print error4

if FIRST_STEP <= 4 and LAST_STEP >= 4:
    print "### CORRECT ALL 'PARTNER WITH NO NAME' AND PARTIAL NAMES"
    partial2_partners = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'search_read', [('name','ilike',' - '),('parent_id','!=',False)], ['id','name','parent_id'] )
    print "partial2_partners"
    print len(partial2_partners)
    for partial in partial2_partners:
        if partial['name'][0:3] == ' - ':
            parents = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'search_read', [('id','=',partial['parent_id'][0])], ['name'] )
            if parents:
                new_data = {'name':parents[0]['name'].strip() + ' ' + partial['name'].strip()}
                sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', [partial['id'],], new_data )
            else:
                if partial['parent_id']:
                    new_data = {'name':partial['parent_id'][1].strip() + ' ' + partial['name'].strip()}
                    sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', [partial['id'],], new_data )

    partial_partners = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'search_read', [('name','ilike','- '),('parent_id','!=',False)], ['id','name','parent_id'] )
    print "partial_partners"
    print len(partial_partners)
    for partial in partial_partners:
        if partial['name'][0:2] == '- ':
            parents = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'search_read', [('id','=',partial['parent_id'][0])], ['name'] )
            if parents:
                new_data = {'name':parents[0]['name'].strip() + ' ' + partial['name'].strip()}
                sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', [partial['id'],], new_data )
            else:
                if partial['parent_id']:
                    new_data = {'name':partial['parent_id'][1].strip() + ' ' + partial['name'].strip()}
                    sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', [partial['id'],], new_data )

    no_name_partners = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'search_read', [('name','=','PARTNER WITH NO NAME'),('parent_id','!=',False)], ['id','name','parent_id'] )
    print "no_name_partners"
    print len(no_name_partners)
    for no_name in no_name_partners:
        parents = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'search_read', [('id','=',no_name['parent_id'][0])], ['name'] )
        if parents:
            new_data = {'name':parents[0]['name'].strip()}
            sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', [no_name['id'],], new_data )
        else:
            if no_name['parent_id']:
                new_data = {'name':no_name['parent_id'][1].strip()}
                sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', [no_name['id'],], new_data )
    
if FIRST_STEP <= 5 and LAST_STEP >= 5:
    print "### WRITE ZIP_ID from address = 'default' to main partner AND DELETE defaults addresses ###"
    def_partners = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'search_read', [('zip_id','!=',False),('type','=','default'),('parent_id','!=',False)], ['id','zip_id','parent_id'] )
    dErasedAddresses = {} # dict of 'default' addresses deleted in favor of the 'main partner' : key = default address id, value = id of main partner
    dDisabledAddresses = {} # dict of 'default' addresses disabled in favor of the 'main partner' : key = default address id, value = id of main partner
    corrected = 0
    for def_partner in def_partners:
        main_partners = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'search_read', [('id','=',def_partner['parent_id'][0])], ['id','zip_id'] )
        if main_partners:
            main_partner = main_partners[0]
            if not main_partner['zip_id']:
                new_data = {'zip_id':def_partner['zip_id'][0],'type':'default'}
                sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', [main_partner['id'],], new_data )
                corrected += 1
                print str(corrected)+'/'+str(len(def_partners))
                try:
                    # we try to delete the default address. Work not if used on some records in another table(s)
                    sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'unlink', [def_partner['id'],] )
                    dErasedAddresses[def_partner['id']] = main_partner['id']
                except:
                    sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', [def_partner['id'],], {'active':False} )
                    dDisabledAddresses[def_partner['id']] = main_partner['id']
    print 'disabled addresses'
    print len(dDisabledAddresses)
    print 'erased addresses'
    print len(dErasedAddresses)
    # correct link to disabled addresses to main partner (invoices, ...)
    # TODO une fois que je saurais comment réagir avec les factures

if FIRST_STEP <= 6 and LAST_STEP >= 6:
    print "### CORRECT TYPES on partners ###"
    cur.execute("SELECT id, base_contact_partner_id FROM res_partner_contact;")
    records = cur.fetchall()
    print 'len records contacts'
    print len(records)
    for rec in records:
        if rec[1]:
            partner = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'read', rec[1], ['type','name'] )
            if not partner['type']:
                partner = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', [rec[1],], {'type':'contact'} )
    cur.execute("SELECT id, partner_id FROM res_partner_address WHERE contact_id in (SELECT id FROM res_partner_contact);")
    records = cur.fetchall()
    print 'len records jobs'
    print len(records)
    for rec in records:
        if rec[1]:
            partner = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'read', rec[1], ['type','name'] )
            if not partner['type']:
                partner = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', [rec[1],], {'type':'contact'} )
    # remise à "default" des fiches en provenance de res_partners
    cur.execute("UPDATE res_partner set type = 'default' WHERE commercial_partner_id = id and type = 'contact' and (membership_amount > 0.01 or vat_subjected) ;")

if FIRST_STEP <= 7 and LAST_STEP >= 7:
    print "### DESACTIVATE SUB-PARTNERS OF INACTIVE MAIN PARTNERS ###"
    inactive_partners = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'search_read', [('is_company','=',True),('child_ids','!=',False),('active','=',False)], ['id','child_ids'] )
    print 'inactive partners with childs'
    print len(inactive_partners)
    child_to_desactivate_ids = []
    for partner in inactive_partners:
        if partner['child_ids']:
            child_to_desactivate_ids.extend(partner['child_ids'])
    print 'childs to desactivate'
    print len(child_to_desactivate_ids)
    sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', child_to_desactivate_ids, {'active':False} )
    
    
if FIRST_STEP <= 8 and LAST_STEP >= 8:
    print "### GET BACK ACTIVITY SECTORS AND CLEAN THEM FROM RES_PARTNER_CATEGORY ##############################"
    if os.path.exists('./res_partner_address_sectors.csv'):
        # 1. we reinject the sectors in the addresses and if default address also on the parent_id
        print "Reinject Activity Sectors"
        hfInput = csv.DictReader(open('./res_partner_address_sectors.csv','r'),delimiter=";",quotechar='"')
        corrected = 0
        wrong = 0
        not_same_partner = 0
        already = 0
        no_new_data = 0
        ids = []
        dSectors = {}
        for ligne in hfInput:
            ids.append(ligne['id'])
            dSectors[int(ligne['id'])] = ligne
        cur.execute("SELECT id, old_partner_id, partner_id FROM res_partner_address where id in (%s);" % ','.join(ids) )
        records = cur.fetchall()
        print 'len records'
        print len(records)
        for rec in records:
            if dSectors.has_key(rec[0]):
                new_partners = []
                try:
                    new_partners = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'search_read', [('id','=',int(rec[2]))], ['parent_id','type','sector1','sector2','sector3'])
                except:
                    print 'no rec[2]'
                if new_partners:
                    new_partner = new_partners[0]
                    if (new_partner['parent_id'] and (new_partner['parent_id'][0] == int(rec[1]))) or ((not new_partner['parent_id']) and str(rec[1]) == 'None'):
                        if not new_partner['sector1'] and not new_partner['sector2'] and not new_partner['sector3']:
                            # inject on address record
                            new_data = {}
                            if dSectors[int(rec[0])]['sector1']:
                                new_data['sector1'] = int(dSectors[int(rec[0])]['sector1'])
                            if dSectors[int(rec[0])]['sector2']:
                                new_data['sector2'] = int(dSectors[int(rec[0])]['sector2'])
                            if dSectors[int(rec[0])]['sector3']:
                                new_data['sector3'] = int(dSectors[int(rec[0])]['sector3'])
                            if new_data:
                                try:
                                    sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', [new_partner['id'],], new_data)
                                    corrected += len(new_data)
                                    if new_partner['type'] == 'default':
                                        # now we try to add it also on the parent partner record
                                        # perhaps it will be not necessary if the default address are in definitive put on main partner reciord
                                        # but in this case, we must change the logic before
                                        if new_partner['parent_id']:
                                            main_partner = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'search_read', [('id','=',new_partner['parent_id'][0])], ['parent_id','type','sector1','sector2','sector3'])[0]
                                            if not main_partner['parent_id'] and not main_partner['sector1'] and not main_partner['sector2'] and not main_partner['sector3']:
                                                sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', [main_partner['id'],], new_data)
                                                corrected += len(new_data)
                                except Exception, erreur:
                                    print erreur
                                    wrong += 1
                            else:
                                no_new_data += 1
                        else:
                            already += 1
                    else:
                        not_same_partner += 1
                else:
                    wrong += 1
            else:
                wrong += 1
        print '--------------'
        print 'reinjected : ' + str(corrected)
        print 'wrong ID : ' + str(wrong)
        print 'already : ' + str(already)
        print 'no new data : ' + str(no_new_data)
        print 'not same partner : ' + str(not_same_partner)

if FIRST_STEP <= 9 and LAST_STEP >= 9:
    # now we search for all 'secteur d'actvités' tags and remove it to put it on sector1, sector2, sector3
    main_categ_id = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner.category', 'search', [('name','=','Activity Sector')])[0]
    new_categ_ids = [main_categ_id,]
    categ_ids = []
    while new_categ_ids:
        categ_ids += new_categ_ids
        new_categs = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner.category', 'read', new_categ_ids, ['id','child_ids'])
        new_categ_ids = []
        for new_cat in new_categs:
            if new_cat['child_ids']:
                new_categ_ids += new_cat['child_ids']
    print 'len categ_ids'
    print len(categ_ids)
    new_sectors = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner.activsector', 'search_read', [], ['id','code'])
    dSectorCode = {}
    for sector in new_sectors:
        dSectorCode[sector['code']] = sector['id']
    categs = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner.category', 'read', categ_ids, ['id','name'], {'lang':'fr_FR'})
    dCatID2SectID = {}
    for categ in categs:
        pos1 = categ['name'].find('[')
        pos2 = categ['name'].find(']')
        if pos1 and pos2 and pos1 < pos2:
            code = categ['name'][pos1+1:pos2]
            if dSectorCode.has_key(code):
                dCatID2SectID[categ['id']] = dSectorCode[code]
            else:
                print 'code ' + code + ' doesnt exist in sectors...'
    print dCatID2SectID
    partners_with_tags = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'search_read', [('category_id','<>',False)], ['category_id','sector1','sector2','sector3'])
    print 'partners with tags'
    print len(partners_with_tags)
    activities = 0
    others = 0
    new_datas = 0
    for partner in partners_with_tags:
        old_data = []
        current_empty_sector = 1
        if partner['sector1']:
            current_empty_sector = 2
            old_data.append(partner['sector1'][0])
            if partner['sector2']:
                current_empty_sector = 3
                old_data.append(partner['sector2'][0])
                if partner['sector3']:
                    current_empty_sector = 4
                    old_data.append(partner['sector3'][0])
        new_data = {}
        for categ_id in partner['category_id']:
            cleaned_categ_ids = []
            if categ_id in categ_ids:
                activities += 1
                if dCatID2SectID.has_key(categ_id):
                    if current_empty_sector <= 3 and dCatID2SectID[categ_id] not in old_data:
                        new_data['sector'+str(current_empty_sector)] = dCatID2SectID[categ_id]
                        current_empty_sector += 1
                        old_data.append(dCatID2SectID[categ_id])
            else:
                cleaned_categ_ids.append(categ_id)
                others += 1
        if new_data:
            new_datas += len(new_data)
        if len(cleaned_categ_ids) != len(partner['category_id']):
            if len(cleaned_categ_ids) == 0:
                new_data['category_id'] = [[5,]]
            else:
                new_data['category_id'] = [[6,0,cleaned_categ_ids]]
        if new_data:
            sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', [partner['id'],], new_data )
            new_data_partner = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'read', [partner['id'],], ['category_id'])
    print 'Secteurs activites detectes : ' + str(activities)
    print 'Autres tags : ' + str(others)
    print 'Secteurs injectes en ajout ' + str(new_datas)

if FIRST_STEP <= 10 and LAST_STEP >= 10:
    # regroup of dir_exclude and dir_presence into dir_selection
    # first we get the value inside the database in case it's migrated
    # but as we are not sure about it, we also get back the values from a CSV table
    # from the original database
    partner_ids = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'search', [])
    index = 0
    size = 500
    while partner_ids[index:index+size]:
        partners = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'read', partner_ids[index:index+size], ['type','dir_presence','dir_exclude'])
        corrections = {'normal':[],'yes':[],'no':[]}
        for partner in partners:
            new = 'normal'
            if partner['type'] != 'contact':
                if partner['dir_presence']:
                    new = 'yes'
                elif partner['dir_exclude']:
                    new = 'no'
            list_of_ids = corrections[new]
            list_of_ids.append(partner['id'])
            corrections[new] = list_of_ids
        for (key,list_ids) in corrections.items():
            if list_ids:
                sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', list_ids, {'dir_selection':key})
                print str(len(list_ids))+ ' set to ' + key
        index += size
        print index
    if os.path.exists('./res_partner_dir_exclude_presence.csv'):
        print "Reinject Memberdirectory exclusions - presences"
        hfInput = csv.DictReader(open('./res_partner_dir_exclude_presence.csv','r'),delimiter=";",quotechar='"')
        corrected = 0
        wrong = 0
        for ligne in hfInput:
            new_value = 'normal'
            if ligne['dir_exclude'] == 't':
                new_value = 'never'
            elif ligne['dir_exclude'] == 't':
                new_value = 'yes'
            if new_value != 'normal':
                partner_ids = [int(ligne['id']),]
                sub_partners = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'search', [('type','in',['default','invoice','delivery','other']),('parent_id','=',int(ligne['id']))])
                if sub_partners:
                    partner_ids.extend(sub_partners)
                    print 'sub partners'
                    print partner_ids
                sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', partner_ids, {'dir_selection':new_value})
        hfInput = csv.DictReader(open('./res_partner_address_dir_exclude.csv','r'),delimiter=";",quotechar='"')
        corrected = 0
        wrong = 0
        original_ids = []
        for ligne in hfInput:
            if ligne['dir_exclude'] == 't':
                original_ids.append(ligne['id'])
        print 'original_ids'
        print original_ids
        if original_ids:
            cur.execute("SELECT id, partner_id FROM res_partner_address WHERE id in (%s);" % ','.join(original_ids)) 
            records = cur.fetchall()
            new_partner_ids = []
            for line in records:
                if line[1]:
                    new_partner_ids.append(line[1])
            print 'new_partner_ids'
            print new_partner_ids
            if new_partner_ids:
                for pid in new_partner_ids:
                    print pid
                    try:
                        sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', [pid,], {'dir_selection':'never'})
                    except Exception, erreur:
                        print '---->Erreur'
if FIRST_STEP <= 11 and LAST_STEP >= 11:
    # regroup of dir_exclude and dir_presence into dir_selection
    # first we get the value inside the database in case it's migrated
    # but as we are not sure about it, we also get back the values from a CSV table
    # from the original database
    partner_ids = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'search', [])
    index = 0
    size = 500
    while partner_ids[index:index+size]:
        partners = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'read', partner_ids[index:index+size], ['magazine_subscription'])
        sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', partner_ids[index:index+size], {'magazine_subscription':'prospect'})
        index += size
        print index
    if os.path.exists('./res_partner_address_mag_sub.csv') and os.path.exists('./res_partner_job_mag_sub.csv') and os.path.exists('./res_partner_contact_mag_sub.csv'):
        print "Reinject Magazine Subscriptions"
        print 'Reinject the codes'
        codes = []
        hfInput = csv.DictReader(open('./res_partner_address_mag_sub.csv','r'),delimiter=";",quotechar='"')
        for ligne in hfInput:
            if ligne['magazine_subscription_source'] and ligne['magazine_subscription_source'] not in codes:
                codes.append(ligne['magazine_subscription_source'])
        hfInput = csv.DictReader(open('./res_partner_job_mag_sub.csv','r'),delimiter=";",quotechar='"')
        for ligne in hfInput:
            if ligne['magazine_subscription_source'] and ligne['magazine_subscription_source'] not in codes:
                codes.append(ligne['magazine_subscription_source'])
        hfInput = csv.DictReader(open('./res_partner_contact_mag_sub.csv','r'),delimiter=";",quotechar='"')
        for ligne in hfInput:
            if ligne['magazine_subscription_source'] and ligne['magazine_subscription_source'] not in codes:
                codes.append(ligne['magazine_subscription_source'])
        print 'codes'
        print codes
        print len(codes)
        dCodes = {}
        for code in codes:
            already_ids = sock_obj.execute(dbname,uid,admin_passwd, 'cci_magazine.subscription_source', 'search', [('code','=',code)])
            if not already_ids:
                print 'adding code'
                new_id = sock_obj.execute(dbname,uid,admin_passwd, 'cci_magazine.subscription_source', 'create', {'name':code,'code':code})
                if new_id:
                    dCodes[code] = new_id
            else:
                dCodes[code] = already_ids[0]
        #
        print 'Reinject addresses'
        hfInput = csv.DictReader(open('./res_partner_address_mag_sub.csv','r'),delimiter=";",quotechar='"')
        corrected = 0
        wrong = 0
        original_ids = []
        dValues =  {}
        for ligne in hfInput:
            original_ids.append(ligne['id'])
            dValues[int(ligne['id'])] = ligne
        print 'original_ids'
        print original_ids
        if original_ids:
            cur.execute("SELECT id, partner_id FROM res_partner_address WHERE id in (%s);" % ','.join(original_ids)) 
            records = cur.fetchall()
            convert_ids = {}
            for line in records:
                if line[1]:
                    convert_ids[line[0]] = line[1]
            print convert_ids
            for key,line in dValues.items():
                new_values = {}
                if line['magazine_subscription'] != 'prospect':
                    new_values['magazine_subscription'] = line['magazine_subscription']
                if line['magazine_subscription_source']:
                    new_values['magazine_subscription_source'] = line['magazine_subscription_source']
                    if dCodes.has_key(line['magazine_subscription_source']):
                        new_values['magazine_subscription_source_id'] = dCodes[line['magazine_subscription_source']]
                if new_values and convert_ids.has_key(key):
                    print convert_ids[key]
                    print new_values
                    try:
                        sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', [int(convert_ids[key]),], new_values)
                    except Exception, erreur:
                        print '--->Erreur'
        #
        print 'Reinject contacts'
        hfInput = csv.DictReader(open('./res_partner_contact_mag_sub.csv','r'),delimiter=";",quotechar='"')
        corrected = 0
        wrong = 0
        original_ids = []
        dValues =  {}
        for ligne in hfInput:
            original_ids.append(ligne['id'])
            dValues[int(ligne['id'])] = ligne
        print 'original_ids'
        print original_ids
        if original_ids:
            cur.execute("SELECT id, base_contact_partner_id FROM res_partner_contact WHERE id in (%s);" % ','.join(original_ids))
            records = cur.fetchall()
            convert_ids = {}
            for line in records:
                if line[1]:
                    convert_ids[line[0]] = line[1]
            print convert_ids
            for key,line in dValues.items():
                new_values = {}
                if line['magazine_subscription'] != 'prospect':
                    new_values['magazine_subscription'] = line['magazine_subscription']
                if line['magazine_subscription_source']:
                    new_values['magazine_subscription_source'] = line['magazine_subscription_source']
                    if dCodes.has_key(line['magazine_subscription_source']):
                        new_values['magazine_subscription_source_id'] = dCodes[line['magazine_subscription_source']]
                if new_values and convert_ids.has_key(key):
                    print convert_ids[key]
                    print new_values
                    try:
                        sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', [int(convert_ids[key]),], new_values)
                    except Exception, erreur:
                        print '--->Erreur'
        #
        print 'Reinject Jobs'
        hfInput = csv.DictReader(open('./res_partner_job_mag_sub.csv','r'),delimiter=";",quotechar='"')
        corrected = 0
        wrong = 0
        original_ids = []
        dValues =  {}
        for ligne in hfInput:
            original_ids.append(ligne['id'])
            dValues[int(ligne['id'])] = ligne
        print 'original_ids'
        print original_ids
        if original_ids:
            cur.execute("SELECT from_job_id, partner_id FROM res_partner_address WHERE from_job_id in (%s);" % ','.join(original_ids))
            records = cur.fetchall()
            convert_ids = {}
            for line in records:
                if line[1]:
                    convert_ids[line[0]] = line[1]
            print convert_ids
            for key,line in dValues.items():
                new_values = {}
                if line['magazine_subscription'] != 'prospect':
                    new_values['magazine_subscription'] = line['magazine_subscription']
                if line['magazine_subscription_source']:
                    new_values['magazine_subscription_source'] = line['magazine_subscription_source']
                    if dCodes.has_key(line['magazine_subscription_source']):
                        new_values['magazine_subscription_source_id'] = dCodes[line['magazine_subscription_source']]
                if new_values and convert_ids.has_key(key):
                    print convert_ids[key]
                    print new_values
                    try:
                        sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', [int(convert_ids[key]),], new_values)
                    except Exception, erreur:
                        print '--->Erreur'
if FIRST_STEP <= 12 and LAST_STEP >= 12:
    # we reinject lastname and firstname on contacts
    cur.execute("SELECT id, base_contact_partner_id, last_name, first_name, name FROM res_partner_contact WHERE base_contact_partner_id > 0;")
    records = cur.fetchall()
    for line in records:
        new_values = {}
        new_values['firstname'] = line[3] or ''
        new_values['lastname'] = line[2] or ''
        if new_values['lastname']:
            try:
                sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', [int(line[1]),], new_values)
            except Exception, erreur:
                print '--->Erreur ' + str(line[1])
                print erreur
        else:
            new_values = {}
            new_values['name'] = line[4] or ''
            if new_values['name']:
                try:
                    sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', [int(line[1]),], new_values)
                except Exception, erreur:
                    print '--->Erreur ' + str(line[1])
                    print erreur
#### ENDING
cur.close()
conn.close()
