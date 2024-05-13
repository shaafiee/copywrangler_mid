def getAccountId(conn, cur, email):
	cur.execute("select id from account where email like %s", (email,))

	allData = cur.fetchall()
	if len(allData) > 0:
		return allData[0][0]

	return False

def createAccount(conn, cur, email):
	try:
		cur.execute("insert into account (email) values (%s) returning id", (email,))
		conn.commit()
		return cur.fetchone()[0]
	except Exception as e:
		print(e)
		return False

def addPasscode(conn, cur, accountId, passcode):
	try:
		cur.execute("update account set passcode = %s where id = %s", (passcode, accountId))
		conn.commit()
		return True
	except Exception as e:
		print(e)
		return False

def verifyAccount(conn, cur, email, passcode):
	cur.execute("select id from account where email like %s and passcode like %s", (email, passcode))

	allData = cur.fetchall()
	if len(allData) > 0:
		accountId = allData[0][0]
		cur.execute("select session_key from session where account_id = %s", (accountId,))
		if cur.rowcount < 1:
			cur.execute("insert into session (account_id) values (%s)", (accountId,))
			conn.commit()
		return accountId

	return False

def checkSession(conn, cur, session):
	cur.execute("select account_id from session left join account on account_id = id where session_key = %s", (session,))
	if cur.rowcount > 0:
		return cur.fetchone()[0]
		
	return False

def isAdmin(conn, cur, session):
	cur.execute("select account.admin from session left join account on account_id = id where session_key = %s", (session,))
	if cur.rowcount > 0:
		if cur.fetchone()[0]:
			return True
		
	return False

def getEmail(conn, cur, session):
	cur.execute("select account.email from session left join account on account_id = id where session_key = %s", (session,))
	if cur.rowcount > 0:
		return cur.fetchone()[0]
		
	return False

