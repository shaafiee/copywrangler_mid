## @package POTTS

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
from fastapi import FastAPI
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
from openai import OpenAI


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
#openaiHeaders = {"Accept": "*/*", "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36", "Content-Type": "application/json", "Origin": "https://" + currentSubdomain + "comfort-works.com", "Referer": "https://" + currentSubdomain + "comfort-works.com/en/my-account/authenticate/", "Authorization": f"Bearer {openai_key}"}
openai_key = getSecret('openai_key')
openai_key = re.sub(r"\s+", "", openai_key)
openai_key = re.sub(r"\n", "", openai_key)
openaiHeaders = {"Accept": "*/*", "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36", "Content-Type": "application/json", "Authorization": f"Bearer {openai_key}"}


def sessionKeyExists(conn, cur, chatKey):
	cur.execute("select session_key from session where session_key like %s", (chatKey,))
	if cur.rowcount > 0:
		return True
	else:
		return False


def cwCheckSession(conn, cur, chatKey):
	cur.execute("select session_data from django_session where session_key like %s", (chatKey,))
	for row in cur:
		sessionData = row[0]
		#userData = pickle.loads(base64.decode(sessionData))
		print(sessionData)

		theString = json.loads(base64.b64decode(sessionData).decode().split(":", 1)[-1])
		print(theString)
		userId = int(theString['_auth_user_id'])
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
	

@app.get('/logs')
async def logs(session: str, queue: int):
	if session is not None or len(session) < 1:
		session = re.sub(r"('|;)", "", session)
	else:
		return {"status": 0, "error": "session key not found"}

	cw_conn, cw_cur = cwDbConnect()

	userId, firstName = cwCheckSession(cw_conn, cw_cur, session)
	if not userId:
		return {"status": 0, "error": "could not verify session"}

	if queue < 1:
		return {"status": 0, "error": "queue ID not found"}

	conn, cur = dbConnect()

	cur.execute("select id, event_type, event_desc, event from log where queue_id = %s", (queue, ))
	results = []
	for row in cur:
		results.append({	"id": row[0],
					"eventClass": row[1],
					"eventSubject": row[2],
					"event": row[3]
			})

	if len(results) < 1:
		return {"status": 0, "error": "no events associated with this queue"}
	
	return {"status": 1, "log": results}
	

@app.post('/prompt')
def prompt(scope: LiteratureScope):
	session = scope.session
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

	questions = scope.questions
	answers = scope.answers

	openai_key = getSecret('openai_key')
	openai_key = re.sub(r"\s+", "", openai_key)
	openai_key = re.sub(r"\n", "", openai_key)
	openaiHeaders = {"Accept": "*/*", "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36", "Content-Type": "application/json", "Authorization": f"Bearer {openai_key}"}

	conversation = []
	for idx, question in enumerate(questions):
		conversation.append({"role": "user", "content": question})
		if len(answers) > idx:
			conversation.append({"role": "assistant", "content": answers[idx]})

	openai_model = getSecret('openai_model')
	returned = requests.post("https://api.openai.com/v1/chat/completions", headers=openaiHeaders, json={"model": openai_model, "messages": conversation})
	retries = 3 
	while returned.status_code == 429 and retries > 0:
		time.sleep(.5)
		returned = requests.post("https://api.openai.com/v1/chat/completions", headers=openaiHeaders, json={"model": "gpt-3.5-turbo", "messages": conversation})
		retries -= 1

	aiResponse = returned.json()
	if returned.status_code == 200:
		answer = aiResponse["choices"][0]["message"]["content"]
		return {"status": 1, "message": "okay", "answer": answer}
	else:
		if "error" in aiResponse.keys(): 
			return {"status": 0, "message": "something went wrong", "code": aiResponse["error"]["code"], "returned": aiResponse}
		else:
			return {"status": 0, "message": "something went wrong", "returned": aiResponse, "code": "unknown"}

	return {"status": 1, "message": "reached end"}
	#gcpHandshake = getSecret("handshake")
	#print(gcpHandshake)
	#hashedHandshake = xor(gcpHandshake, "12345abcde")
	#print(hashedHandshake)
	#return {"status": 1, "message": "found", "handshake": hashedHandshake}


@app.post('/assist')
def assist(scope: LiteratureScope):
	session = scope.session
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

	openai_key = getSecret('openai_key')
	openai_key = re.sub(r"\s+", "", openai_key)
	openai_key = re.sub(r"\n", "", openai_key)
	openaiHeaders = {"Accept": "*/*", "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36", "Content-Type": "application/json", "Authorization": f"Bearer {openai_key}", "OpenAI-Beta": "assistants=v1"}
	openai_model = getSecret('openai_model')
	client = OpenAI(api_key=openai_key)

	threadId = None
	assistantId = None
	cur.execute("select thread_id, assistant_id from user where user_id = %s", (userId,))
	if cur.rowcount > 0:
		threadId, assistantId = cur.fetchone()
		#returned = requests.post("https://api.openai.com/v1/threads", headers=openaiHeaders, json={"model": openai_model, "messages": conversation})
	else:
		assistantId = re.sub(r"(\s|\n)+", "", getSecret('openai_assistant'))
		thread = client.beta.threads.create()
		threadId = thread.id
		cur.execute("update user set thread_id = %s, assistant_id = %s, thread_created = now() where user_id = %s", (threadId, assistantId, userId))
		conn.commit()

	questions = scope.questions
	answers = scope.answers

	#conversation = []
	if len(questions) > 0:
		for idx, question in enumerate(questions):
			message = client.beta.threads.messages.create (
				thread_id=threadId,
				role="user",
				content=question
			)
			if (len(answers) - 1) >= idx:
				message = client.beta.threads.messages.create (
					thread_id=threadId,
					role="assistant",
					content=answers[idx]
				)

		run = client.beta.threads.runs.create(
			thread_id=threadId,
			assistant_id=assistantId,
			instructions=f"Please address the user as {firstName}. The user has a regular account."
		)

		while run.status in ['queued', 'in_progress', 'cancelling']:
			time.sleep(2)
			run = client.beta.threads.runs.retrieve(
				thread_id=threadId,
				run_id=run.id
			)
	
		if run.status == 'completed':
			messages = client.beta.threads.messages.list(
				thread_id=threadId
			)

			return {"status": 1, "message": "okay", "answer": messages}
			#return {"status": 1, "message": "okay", "answer": messages['data'][0]['content'][0]['text']['value']}
		else:
			return {"status": 0, "message": "something went wrong", "run": run.status}
			
				
	return {"status": 0, "message": "something went wrong"}


if __name__ == '__main__':
	print("STARTING")
	GCP_PROJECT_ID = requests.get("http://metadata.google.internal/computeMetadata/v1/project/project-id")
	print(GCP_PROJECT_ID)
	app.run(host="127.0.0.1", port=8080, debug=False)


