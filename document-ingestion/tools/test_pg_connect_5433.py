import os
import psycopg2

host='localhost'
port=5433
user='doc_user'
password='doc_password'
db='documents_db'
print('Trying', host, port, user, db)
try:
    conn=psycopg2.connect(dbname=db,user=user,password=password,host=host,port=port,connect_timeout=5)
    print('Connected OK to',db)
    conn.close()
except Exception as e:
    print('Failed:',e)
