#!/usr/bin/python
#-*- coding: utf-8 -*-

import xmlrpclib
import os
import csv
import psycopg2
import sys

execfile('../params.txt')

url = 'http://%s/xmlrpc' % connect['url']
sock_obj = xmlrpclib.ServerProxy(url+'/object')
sock_connect = xmlrpclib.ServerProxy(url+'/common')

admin_login = connect['admin_login']
admin_passwd = connect['admin_passwd']
dbname = connect['dbname']
psql_server = connect['pserver']
psql_user = connect['puser']
psql_pw = connect['ppassword']

#dbname = 'ccilvn_201703' # to force the database name 

uid = sock_connect.login(dbname, admin_login, admin_passwd)
print "UID : " + str(uid)

#conn = psycopg2.connect(database=dbname, user=psql_user, password=psql_pw, host=psql_server)
#cur = conn.cursor()

partner_ids = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'search', [('function_code_label','<>',False)] )
print len(partner_ids)

functions = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner.function', 'search_read', [], ['code'] )
dFunctions = {}
for function in functions:
    dFunctions[function['code']] = function['id']
print len(dFunctions)

partners = sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'read', partner_ids, ['function_code_label'] )
for partner in partners:
    if partner['function_code_label']:
        function_codes = ''
        function_ids = []
        for letter in partner['function_code_label']:
            if dFunctions.has_key(letter):
                function_codes += letter + ','
                if dFunctions[letter] not in function_ids:
                    function_ids.append(dFunctions[letter])
        if function_codes:
            sock_obj.execute(dbname,uid,admin_passwd, 'res.partner', 'write', [partner['id'],], {'function_codes':function_codes,'function_ids':[(6,0,function_ids)]})
    print partner['id']
#### ENDING
#cur.close()
#conn.close()
