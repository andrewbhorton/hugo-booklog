import os
import psycopg2
import csv

conn = psycopg2.connect(
    host="localhost",
    database="booklog_db",
    user=os.environ['DB_USERNAME'],
    password=os.environ['DB_PASSWORD'])

cur = conn.cursor()

cur.execute('DROP TABLE IF EXISTS hugos;')
cur.execute('CREATE TABLE hugos (id SERIAL PRIMARY KEY, year INTEGER, author VARCHAR (50) NOT NULL, title varchar (150) NOT NULL, read INTEGER, hasnotes INTEGER);')

cur.execute('DROP TABLE IF EXISTS users;')
cur.execute('CREATE TABLE users (userid SERIAL PRIMARY KEY, username VARCHAR (50), hash VARCHAR (150));')

cur.execute('DROP TABLE IF EXISTS userdata;')
cur.execute('CREATE TABLE userdata (userid INTEGER, bookid INTEGER, notes VARCHAR (5000), rating INTEGER, read INTEGER);')

file = open('static/hugos.csv', encoding='utf-8')
contents = csv.reader(file)
insert_records = "INSERT INTO hugos (year, author, title) VALUES (%s, %s, %s)"
cur.executemany(insert_records, contents)

conn.commit()

cur.close()
conn.close()