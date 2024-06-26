# @package POTTS

## @file app.py

import time
import re
#import psycopg2
import mysql.connector
import os
import smtplib, ssl
import random
#import dns.resolver
from account_lib import *
from db_lib import *
#from email.mime.text import MIMEText
#from email.mime.multipart import MIMEMultipart
from fastapi import FastAPI, Response
#from fluidcrypt.fluidcrypt import *
from gcp_secrets.secrets import getSecret
import requests
from pydantic import BaseModel
from data.base import *
#import add from toolset.alignProducts import translateProduct, translateProdBatch
#import pickle
import json
import base64
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import traceback
#from openai import OpenAI

from google.auth.transport.requests import Request
from google.oauth2 import service_account
#from google.auth import jwt
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import gspread
from hashlib import sha256
from gspread_formatting import *


app = FastAPI()


origins = ["https://ai.comfort-works.com", "https://pre-potts.comfort-works.com", "http://pre-potts-frontend.comfort-works.com", "http://pre-potts-middleware.comfort-works.com"]


app.add_middleware(
	CORSMiddleware,
	allow_origins=origins,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


currentSubdomain = "cw40"
headers = {"Accept": "*/*", "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36", "Content-Type": "application/json", "Origin": "https://" + currentSubdomain + "comfort-works.com", "Referer": "https://" + currentSubdomain + "comfort-works.com/en/my-account/authenticate/"}


def sessionKeyExists(conn, cur, chatKey):
	cur.execute("select session_key from session where session_key like %s", (chatKey,))
	if cur.rowcount > 0:
		return True
	else:
		return False


def cwCheckSession(conn, cur, chatKey, admin = False):
	cur.execute("select session_data from django_session where session_key like %s", (chatKey,))
	for row in cur:
		sessionData = row[0]
		#userData = pickle.loads(base64.decode(sessionData))
		print(sessionData)

		theString = json.loads(base64.b64decode(sessionData).decode().split(":", 1)[-1])
		print(theString)
		userId = int(theString['_auth_user_id'])
		if admin:
			cur.execute("select user_id, first_name from account_user_groups left join account_user on account_user.id = user_id  where user_id = %s and account_user.is_superuser = 1", (userId,))
		else:
			cur.execute("select user_id, first_name from account_user_groups left join account_user on account_user.id = user_id  where user_id = %s", (userId,))
	
		for subrow in cur:
			if subrow[0] == userId:
				returnList = []
				returnList.append(userId)
				returnList.append(subrow[1])
				return returnList
			else:
				return False
		return False
	else:
		return False


def newKey(keyLength = 18):
	curKeyLength = 0
	key = ""
	while curKeyLength <= keyLength:
		randNo = random.randint(48, 122)
		if (randNo >= 58 and randNo <= 64) or (randNo >= 91 and randNo <= 96):
			continue
		else:
			key = key + chr(randNo)
			curKeyLength += 1
	return key		


@app.get('/', response_class=HTMLResponse)
async def landing():
	with open("/filestore/default.html") as IF:
		fileData = IF.readlines()
		htmlData = ""
		for htmlLine in fileData:
			htmlData = htmlData + htmlLine
		return htmlData


@app.get('/pullcheck')
def pullCheck(session):
	if session is not None or len(session) < 1:
		session = re.sub(r"('|;)", "", session)
	else:
		return {"status": 0, "error": "session key not found"}

	#for refCode in scope.products:
	#	if not re.match(r"^[a-zA-Z0-9_\-\/\s]*$", refCode):
	#		return {"status": 0, "error": f"incorrect ref code {refCode}"}

	cw_conn, cw_cur = cwDbConnect()

	userId, firstName = cwCheckSession(cw_conn, cw_cur, session)
	if not userId:
		return {"status": 0, "error": "could not verify session"}

	conn, cur = dbConnect()

	cur.execute("select id, pages, collections, scope from queue where pull = 1 and (done is NULL or done <> 1) and (term is NULL or term <> 1)")
	if cur.rowcount > 0:
		return {"status": 0, "error": "A pull request is still being processed"}
	else:
		return {"status": 1, "content": "No pull requests"}


@app.post('/pull')
def pull(scope: PullScope):
	session = scope.session
	if session is not None or len(session) < 1:
		session = re.sub(r"('|;)", "", session)
	else:
		return {"status": 0, "error": "session key not found"}

	#for refCode in scope.products:
	#	if not re.match(r"^[a-zA-Z0-9_\-\/\s]*$", refCode):
	#		return {"status": 0, "error": f"incorrect ref code {refCode}"}

	cw_conn, cw_cur = cwDbConnect()

	userId, firstName = cwCheckSession(cw_conn, cw_cur, session, True)
	if not userId:
		return {"status": 0, "error": "could not verify session"}

	conn, cur = dbConnect()

	cur.execute("select id, pages, collections, scope from queue where pull = 1 and (done is NULL or done <> 1) and (term is NULL or term <> 1)")
	if cur.rowcount > 0:
		return {"status": 0, "error": "A pull request is still being processed"}

	cur.execute("insert into queue (pull, pages, collections, scope, assets) values (1, %s, %s, %s, %s)", (scope.pages, scope.collections, scope.scope, scope.assets))
	conn.commit()
	return {"status": 1, "content": "Pull request queued"}


@app.get('/lasttimes')
def lasttimes(session: str):
	if session is not None or len(session) < 1:
		session = re.sub(r"('|;)", "", session)
	else:
		return {"status": 0, "error": "session key not found"}

	cw_conn, cw_cur = cwDbConnect()

	userId, firstName = cwCheckSession(cw_conn, cw_cur, session)
	if not userId:
		return {"status": 0, "error": "could not verify session"}

	conn, cur = dbConnect()

	try:
		cur.execute("select unix_timestamp(updated) from page order by id desc limit 1")
	except Exception as e:
		print(e)
		print(traceback.format_exc())
		return {"status": 0, "error": str(traceback.format_exec())}
	pageTimestamp = cur.fetchone()[0]

	return {"status": 1, "content": {"page": pageTimestamp, "collection": 0}}
	

@app.post('/pullcontent')
def pullcontent(scope: PullScope):
	session = scope.session
	if session is not None or len(session) < 1:
		session = re.sub(r"('|;)", "", session)
	else:
		return {"status": 0, "error": "session key not found"}

	cw_conn, cw_cur = cwDbConnect()

	userId, firstName = cwCheckSession(cw_conn, cw_cur, session)
	if not userId:
		return {"status": 0, "error": "could not verify session"}

	conn, cur = dbConnect()
	pages = []
	collections = []
	assets = []

	if scope.pages == 1:
		cur.execute("select id, handle, template_suffix, langs from page order by handle")
		rows = cur.fetchall()
		for row in rows:
			pages.append(row)

	if scope.collections == 1:
		cur.execute("select id, handle, title, langs from collection order by handle")
		rows = cur.fetchall()
		for row in rows:
			collections.append(row)

	if scope.assets == 1:
		cur.execute("select admin_graphql_api_id from asset")
		rows = cur.fetchall()
		for row in rows:
			assets.append(row)

	return {"status": 1, "content": {"pages": pages, "collections": collections, "assets": assets}}


@app.post('/pulltrans')
def pulltrans(scope: PullTransScope):
	if scope.resource == 0:
		return {"status": 0, "error": "must specify a resource"}

	session = scope.session
	if session is not None or len(session) < 1:
		session = re.sub(r"('|;)", "", session)
	else:
		return {"status": 0, "error": "session key not found"}

	cw_conn, cw_cur = cwDbConnect()

	userId, firstName = cwCheckSession(cw_conn, cw_cur, session)
	if not userId:
		return {"status": 0, "error": "could not verify session"}

	conn, cur = dbConnect()

	resourceTrans = {}
	if scope.resource > 0:
		cur.execute("select id, tr_key, tr_value, lang from translatable where resource_id = %s and resource_type = %s", (scope.resource, scope.resourceType))
		rows = cur.fetchall()

		for row in rows:
			if row[3] not in resourceTrans.keys():
				resourceTrans[row[3]] = {}
			if row[1] not in resourceTrans[row[3]].keys():
				resourceTrans[row[3]][row[1]] = {}
			resourceTrans[row[3]][row[1]] = {'id': row[0], 'value': row[2]}

	#if scope.collection == 1:

	return {"status": 1, "content": {"pages": resourceTrans}}


def validValue(value):
	isValid = True
	if re.search(r"^\s*(https:\/\/|shopify:\/\/)\S*\s*", value, re.M) and not re.search(r"(<|>)", value, re.M):
		isValid = False
	if re.search(r"^[A-Za-z0-9]+$", value):
		isValid = False
	if re.search(r"^\s*<svg.*</svg>\s*$", value, re.M):
		isValid = False
	return isValid
	


def compileCSV(rows, isColl = False, isAsset = False):
	#collTitle = {"title": 5, "description": 6, "body_html": 7, "descriptionHtml": 7}
	collTitle = {"title": 5, "body_html": 7}
	theLangs = ["en", "de", "fr", "es", "ja"]
	langsAdded = []
	csv = ""
	csvLangs = []
	currentValues = []
	current = []
	currentKey = None
	langsComposed = False
	body = []
	theValue = None
	keyLang = {}
	currentLang = None
	totalValues = 0
	marked = []
	counter = 0
	for row in rows:
		if row[2] != currentKey:
			if currentKey is not None:
				langsComposed = True
				#preJoin = ','.join(current)
				totalValues = 0
				for theLang in theLangs:
					if theLang in keyLang.keys():
						#if isColl and theLang != 'en':
						#	current.append(keyLang[theLang])
						#else:
						#	if not isColl or (isColl and theLang == 'en' and theLang in keyLang.keys()):
						#		current.append(keyLang[theLang])
						current.append(keyLang[theLang])
						totalValues += 1
					else:
						current.append('')
				counter = counter + 1
				if totalValues < len(theLangs):
					marked.append(counter)
				#if not (len(langsAdded) >= len(theLangs)) and 'en' in keyLang.keys() and validValue(keyLang['en']):
				if 'en' in keyLang.keys() and validValue(keyLang['en']):
					if isColl:
						if not re.search(r"^[A-Za-z0-9]+(\-|_)[A-Za-z0-9]+((\-|_)[A-Za-z0-9]+)*", keyLang['en']) and currentKey in collTitle.keys():
							body.append(current)
					else:
						if isAsset:
							if currentKey in ["title", "meta_title", "body_html"]:
								body.append(current)
						else:
							body.append(current)
				#csv = f"{csv}{preJoin}\n"
				current = []
				langsAdded = []
				keyLang = {}
			currentKey = row[2]
			theHandle = row[1] if row[1] is not None else ""
			theKey = row[2] if row[2] is not None else ""
			#if totalValues == len(theLangs) and (theKey in ["title", "meta_title", "body_html"] or isAsset) and validValue(keyLang('en')):
			if True: 
				if isColl:
					theValue = row[collTitle[theKey]] if row[collTitle[theKey]] is not None else ""
					currentLang = 'en'
					current = [f"https://comfort-works.com/collections/{theHandle}", theHandle, theKey]
					keyLang[currentLang] = theValue
					theValue = row[3] if row[3] is not None else ""
					#current.append('"' + theValue + '"')
					currentLang = row[4]
					langsAdded.append(currentLang)
					keyLang[currentLang] = theValue
				else:
					if isAsset:
						theValue = row[3] if row[3] is not None else ""
						current = [row[5], "", theKey]
						currentLang = row[4]
						langsAdded.append(currentLang)
						keyLang[currentLang] = theValue
					else:
						theValue = row[3] if row[3] is not None else ""
						#current = [row[0], theHandle, theKey]
						current = [f"https://comfort-works.com/pages/{theHandle}", theHandle, theKey]
						currentLang = row[4]
						langsAdded.append(currentLang)
						keyLang[currentLang] = theValue
		else:
			currentLang = row[4].lower()
			theValue = row[3] if row[3] is not None else ""
			keyLang[currentLang] = theValue
			langsAdded.append(currentLang)
			if currentLang not in theLangs:
				theLangs.append(currentLang)
			#theValue = row[3] if row[3] is not None else ""
			#current.append('"' + theValue + '"')
		#if row[4] not in csvLangs:
		#	csvLangs.append(row[4])
	header = ["", "", ""] + theLangs
	body.insert(0, header)
	#preJoin = ','.join(header)
	#csv = f"{preJoin}\n{csv}"
	return {"body": body, "marked": marked}


@app.get('/pagecsv')
def pageCSV(session: str, category: int = 1):
	if session is not None or len(session) < 1:
		session = re.sub(r"('|;)", "", session)
	else:
		return {"status": 0, "error": "session key not found"}

	cw_conn, cw_cur = cwDbConnect()

	userId, firstName = cwCheckSession(cw_conn, cw_cur, session, True)
	if not userId:
		return {"status": 0, "error": "could not verify session"}

	conn, cur = dbConnect()

	service_account_info = getSecret("gsheetapi")
	with open("gsheetapi.json", "w") as OFILE:
		OFILE.write(service_account_info)
	OFILE.close()


	title = "Content in Shopify"

	#scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
	#creds = service_account.Credentials.from_service_account_file("gsheetapi.json", scopes=scopes)
	#service = build("sheets", "v4", credentials=creds)
	#spreadsheet = {"properties": {"title": title}}
	#spreadsheet = (service.spreadsheets().create(body=spreadsheet, fields="spreadsheetId").execute())


	gsheetid = None
	cur.execute("select gsheetid from gsheet")
	if cur.rowcount > 0:
		gsheetid = cur.fetchone()[0]

	scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
	creds = service_account.Credentials.from_service_account_file("gsheetapi.json", scopes=scopes)
	client = gspread.authorize(creds)
	spreadsheet = None
	if gsheetid is None:
		spreadsheet = client.create(title)
		gsheetid = spreadsheet.id
		cur.execute("delete from gsheet")
		conn.commit()
		cur.execute("insert into gsheet (gsheetid) values (%s)", (gsheetid, ))
		conn.commit()
	else:
		try:
			spreadsheet = client.open_by_key(gsheetid)
		except:
			spreadsheet = client.create(title)
			gsheetid = spreadsheet.id
			cur.execute("delete from gsheet")
			conn.commit()
			cur.execute("insert into gsheet (gsheetid) values (%s)", (gsheetid, ))
			conn.commit()


	spreadsheet.share('comfort-works.com', perm_type='domain', role='writer')


	try:
		worksheet = spreadsheet.worksheet("Pages")
		spreadsheet.del_worksheet(worksheet)
	except:
		pass
	cur.execute("select page.id, page.handle, tr_key, tr_value, lang from translatable join page on resource_id = page.id and resource_type = 1 order by resource_id, tr_key, lang")
	rows = cur.fetchall()
	compiled = compileCSV(rows)
	body = compiled['body']

	lines = len(body)
	columns = len(body[0])
	endColumn = chr(65 + columns)
	rangeName = f"A1:{endColumn}{lines}"
	wrapRangeName = f"D1:{endColumn}{lines}"

	worksheet = spreadsheet.add_worksheet("Pages", rows=lines, cols=columns)

	worksheet.update(rangeName, body)
	toFormat = []
	for needTrans in compiled["marked"]:
		toFormat.append((f"A{needTrans}:{endColumn}{needTrans}", cellFormat(backgroundColor=(.99, .8, .8))))
	format_cell_ranges(worksheet, toFormat)
	worksheet.format(wrapRangeName, {"wrapStrategy": "WRAP"})


	try:
		worksheet = spreadsheet.worksheet("Collections")
		spreadsheet.del_worksheet(worksheet)
	except:
		pass
	cur.execute("select collection.id, collection.handle, tr_key, tr_value, lang, title, description, descriptionHtml from translatable join collection on resource_id = collection.id and resource_type = 2 where tr_key not like 'handle' order by resource_id, tr_key, lang")
	rows = cur.fetchall()
	compiled = compileCSV(rows)
	body = compiled['body']

	lines = len(body)
	columns = len(body[0])
	endColumn = chr(65 + columns)
	rangeName = f"A1:{endColumn}{lines}"
	wrapRangeName = f"D1:{endColumn}{lines}"

	worksheet = spreadsheet.add_worksheet("Collections", rows=lines, cols=columns)

	worksheet.update(rangeName, body)
	toFormat = []
	for needTrans in compiled["marked"]:
		toFormat.append((f"A{needTrans}:{endColumn}{needTrans}", cellFormat(backgroundColor=(.99, .8, .8))))
	format_cell_ranges(worksheet, toFormat)
	worksheet.format(wrapRangeName, {"wrapStrategy": "WRAP"})


	try:
		worksheet = spreadsheet.worksheet("Assets")
		spreadsheet.del_worksheet(worksheet)
	except:
		pass
	cur.execute("select asset.id, asset.admin_graphql_api_id, tr_key, tr_value, lang, exact_url from translatable join asset on resource_id = asset.id and resource_type = 3 where tr_key not like 'handle' order by tr_key")
	rows = cur.fetchall()
	compiled = compileCSV(rows)
	body = compiled['body']

	lines = len(body)
	columns = len(body[0])
	endColumn = chr(65 + columns)
	rangeName = f"A1:{endColumn}{lines}"
	wrapRangeName = f"D1:{endColumn}{lines}"

	worksheet = spreadsheet.add_worksheet("Assets", rows=lines, cols=columns)

	worksheet.update(rangeName, body)
	toFormat = []
	for needTrans in compiled["marked"]:
		toFormat.append((f"A{needTrans}:{endColumn}{needTrans}", cellFormat(backgroundColor=(.99, .8, .8))))
		#toFormat.append((f"A{needTrans}:{endColumn}{needTrans}", {"backgroundColor": {"red": .99, "green": .80, "blue": .80, "alpha": 1}}))
	format_cell_ranges(worksheet, toFormat)
	worksheet.format(wrapRangeName, {"wrapStrategy": "WRAP"})


	#delWorksheet = spreadsheet.get_worksheet(0)
	#spreadsheet.del_worksheet(delWorksheet)

	return {"status": 1, "gsheet": gsheetid}


def updateItem(conn, cur, table, handle, key, value, lang):
	if value is None or value == "" or len(value) < 1:
		return False
	if table == 'asset':
		cur.execute(f"select id from {table} limit 1")
	else:
		cur.execute(f"select id from {table} where handle = %s", (handle, ))
	if cur.rowcount < 1:
		return False
	resourceId = cur.fetchone()[0]
	key = key.rstrip()
	key = key.lstrip()
	value = value.rstrip()
	value = value.lstrip()
	cur.execute("select altered from translatable where resource_id = %s and tr_key like %s and tr_value like %s and lang = %s", (resourceId, key, value, lang))
	if cur.rowcount > 0:
		return False
	if lang == 'en':
		digest = hasher(value)
		cur.execute("update translatable set tr_value = %s, digest = %s, altered = 1 where tr_key = %s and resource_id = %s and lang = %s", (value, digest, key, resourceId, lang))
	else:
		cur.execute("update translatable set tr_value = %s, altered = 1 where tr_key = %s and resource_id = %s and lang = %s", (value, key, resourceId, lang))
	conn.commit()
	return True


def hasher(value):
	if value is None:
		return ""
	return sha256(value.encode("utf-8")).hexdigest()


@app.post('/updatetrans')
def updateTrans(scope: UpdateTrans):
	session = scope.session
	if session is not None or len(session) < 1:
		session = re.sub(r"('|;)", "", session)
	else:
		return {"status": 0, "error": "session key not found"}

	cw_conn, cw_cur = cwDbConnect()

	userId, firstName = cwCheckSession(cw_conn, cw_cur, session)
	if not userId:
		return {"status": 0, "error": "could not verify session"}

	conn, cur = dbConnect()

	if scope.lang == 'en':
		digest = hasher(scope.trValue)
		cur.execute("update translatable set tr_value = %s, digest = %s, altered = 1 where resource_id = %s and tr_key = %s and lang = %s", (scope.trValue, digest, scope.resource, scope.trKey, scope.lang))
	else:
		cur.execute("update translatable set tr_value = %s, altered = 1 where resource_id = %s and tr_key = %s and lang = %s", (scope.trValue, scope.resource, scope.trKey, scope.lang))
	conn.commit()
	
	return {"status": 1, "content": "saved"}


@app.post('/upload')
def uploadSheet(scope: UploadSheet):
	session = scope.session
	if session is not None or len(session) < 1:
		session = re.sub(r"('|;)", "", session)
	else:
		return {"status": 0, "error": "session key not found"}

	cw_conn, cw_cur = cwDbConnect()

	userId, firstName = cwCheckSession(cw_conn, cw_cur, session)
	if not userId:
		return {"status": 0, "error": "could not verify session"}

	conn, cur = dbConnect()

	service_account_info = getSecret("gsheetapi")
	with open("gsheetapi.json", "w") as OFILE:
		OFILE.write(service_account_info)
	OFILE.close()

	scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
	creds = service_account.Credentials.from_service_account_file("gsheetapi.json", scopes=scopes)
	client = gspread.authorize(creds)
	spreadsheet = client.open_by_url(scope.url)
	gsheetid = spreadsheet.id

	#spreadsheet.share(None, perm_type='anyone', role='writer')
	pageSheet = spreadsheet.get_worksheet(0)
	collSheet = spreadsheet.get_worksheet(1)
	assetSheet = spreadsheet.get_worksheet(2)
	pages = pageSheet.get_all_values()
	colls = collSheet.get_all_values()
	assets = assetSheet.get_all_values()

	langs = ["en", "de", "fr", "es", "ja"]
	for jdx, lang in enumerate(langs):
		for idx, page in enumerate(pages):
			if idx > 0:
				for jdx in range(5):
					updateItem(conn, cur, "page", pages[idx][1], pages[idx][2], pages[idx][3 + jdx], lang)

		for idx, coll in enumerate(colls):
			if idx > 0:
				for jdx in range(5):
					updateItem(conn, cur, "collection", colls[idx][1], colls[idx][2], colls[idx][3 + jdx], lang)

		for idx, coll in enumerate(assets):
			if idx > 0:
				for jdx in range(5):
					updateItem(conn, cur, "asset", colls[idx][1], colls[idx][2], colls[idx][3 + jdx], lang)

	return {"status": 1, "content": "saved"}


@app.post('/push')
def push(session: str):
	if session is not None or len(session) < 1:
		session = re.sub(r"('|;)", "", session)
	else:
		return {"status": 0, "error": "session key not found"}

	#for refCode in scope.products:
	#	if not re.match(r"^[a-zA-Z0-9_\-\/\s]*$", refCode):
	#		return {"status": 0, "error": f"incorrect ref code {refCode}"}

	cw_conn, cw_cur = cwDbConnect()

	userId, firstName = cwCheckSession(cw_conn, cw_cur, session, True)
	if not userId:
		return {"status": 0, "error": "could not verify session"}

	conn, cur = dbConnect()

	cur.execute("select id, pages, collections, scope from queue where push = 1 and (done is NULL or done <> 1) and (term is NULL or term <> 1)")
	if cur.rowcount > 0:
		return {"status": 0, "error": "A push request is still being processed"}

	cur.execute("insert into queue (push) values (1)")
	conn.commit()
	return {"status": 1, "content": "Push request queued"}


@app.get('/pushcheck')
def pushCheck(session):
	if session is not None or len(session) < 1:
		session = re.sub(r"('|;)", "", session)
	else:
		return {"status": 0, "error": "session key not found"}

	#for refCode in scope.products:
	#	if not re.match(r"^[a-zA-Z0-9_\-\/\s]*$", refCode):
	#		return {"status": 0, "error": f"incorrect ref code {refCode}"}

	cw_conn, cw_cur = cwDbConnect()

	userId, firstName = cwCheckSession(cw_conn, cw_cur, session)
	if not userId:
		return {"status": 0, "error": "could not verify session"}

	conn, cur = dbConnect()

	cur.execute("select id, pages, collections, scope from queue where push = 1 and (done is NULL or done <> 1) and (term is NULL or term <> 1)")
	if cur.rowcount > 0:
		return {"status": 0, "error": "A push request is still being processed"}
	else:
		return {"status": 1, "content": "No push requests"}


if __name__ == '__main__':
	print("STARTING")
	GCP_PROJECT_ID = requests.get("http://metadata.google.internal/computeMetadata/v1/project/project-id")
	print(GCP_PROJECT_ID)
	app.run(host="127.0.0.1", port=8080, debug=False)


