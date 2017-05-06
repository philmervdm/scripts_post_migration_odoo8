#!/usr/bin/python
#-*- coding: utf-8 -*-

import xmlrpclib
import os
import csv
import psycopg2
import sys

execfile('../params.txt')

def lower_wo_accent(name):
    good_name = name.lower().replace (u'é','e').replace (u'è','e').replace (u'â','a').replace (u'ê','e')
    if len(good_name) > 2 and (good_name[-2:] == ' 1' or good_name[-2:] == ' 2'):
        good_name = good_name[:-2]
    return good_name
FIRST_STEP = 1
LAST_STEP = 1

url = 'http://%s/xmlrpc' % connect['url']
sock_obj = xmlrpclib.ServerProxy(url+'/object')
sock_connect = xmlrpclib.ServerProxy(url+'/common')

admin_login = connect['admin_login']
admin_passwd = connect['admin_passwd']
dbname = connect['dbname']
psql_server = connect['pserver']

dbname = 'test_addr'

uid = sock_connect.login(dbname, admin_login, admin_passwd)
print "UID : " + str(uid)

conn = psycopg2.connect(database=dbname, user="odoo", password="odoo", host="172.17.0.2")
cur = conn.cursor()

# Ajoute les liens vers les pays dans les codes postaux s'ils peuvent être retrouvés
if FIRST_STEP <= 1 and LAST_STEP >= 1:
    #cur.execute("SELECT id FROM res_partner WHERE type = 'contact';")
    #records = cur.fetchall()
    #print 'len records partners of type contact'
    #print len(records)
    
    # ABOVE : MAINLY PERSONAL ADDRESSES => left as 'contact' now
    #
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
#### ENDING
cur.close()
conn.close()
