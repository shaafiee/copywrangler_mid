#import os
#import psycopg2
import mysql.connector
from gcp_secrets.secrets import getSecret

def dbConnect():
	#database = os.getenv('database')
	database = getSecret('copywrangler_mid_database')
	if not database:
		#conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), database='DB_NAME', user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
		#return [conn, conn.cursor()]
		conn = mysql.connector.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), database='DB_NAME', user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
		return [conn, conn.cursor()]
	else:
		db_lines = database.split("\n")
		db_val = {}
		for db_line in db_lines:
			db_vals = db_line.split(':', 1)
			db_val[db_vals[0]] = db_vals[1]
		#conn = psycopg2.connect(host=db_val['DB_HOST'], database=db_val['DB_NAME'], user=db_val['DB_USER'], password=db_val['DB_PASSWORD'])
		#return [conn, conn.cursor()]
		conn = mysql.connector.connect(unix_socket=db_val['DB_HOST'], database=db_val['DB_NAME'], user=db_val['DB_USER'], password=db_val['DB_PASSWORD'])
		return [conn, conn.cursor(buffered=True)]


def cwDbConnect():
	#database = os.getenv('database')
	database = getSecret('cw_database')
	if not database:
		#conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), database='DB_NAME', user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
		conn = mysql.connector.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), database='DB_NAME', user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
		return [conn, conn.cursor()]
	else:
		db_lines = database.split("\n")
		db_val = {}
		for db_line in db_lines:
			db_vals = db_line.split(':', 1)
			db_val[db_vals[0]] = db_vals[1]
		#conn = psycopg2.connect(host=db_val['DB_HOST'], database=db_val['DB_NAME'], user=db_val['DB_USER'], password=db_val['DB_PASSWORD'])
		conn = mysql.connector.connect(unix_socket=db_val['DB_HOST'], database=db_val['DB_NAME'], user=db_val['DB_USER'], password=db_val['DB_PASSWORD'])
		return [conn, conn.cursor()]

