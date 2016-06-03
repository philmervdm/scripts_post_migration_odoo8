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
FIRST_STEP = 3

url = 'http://%s/xmlrpc' % connect['url']
sock_obj = xmlrpclib.ServerProxy(url+'/object')
sock_connect = xmlrpclib.ServerProxy(url+'/common')

admin_login = connect['admin_login']
admin_passwd = connect['admin_passwd']
dbname = connect['dbname']
psql_server = connect['pserver']

uid = sock_connect.login(dbname, admin_login, admin_passwd)
print "UID : " + str(uid)

conn = psycopg2.connect(database="ccilvn_20160303_v3_work", user="odoo", password="odoo", host="172.17.0.2")
cur = conn.cursor()

# Ajoute les liens vers les pays dans les codes postaux s'ils peuvent être retrouvés
if FIRST_STEP <= 1:
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
if FIRST_STEP <= 2:
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
if FIRST_STEP <= 3:
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

BOUM

if FIRST_STEP <= 4:
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
                new_partners = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'search_read', [('id','=',int(rec[2]))], ['parent_id','type','sector1','sector2','sector3'])
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

if FIRST_STEP <= 5:
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
#### ENDING
cur.close()
conn.close()
