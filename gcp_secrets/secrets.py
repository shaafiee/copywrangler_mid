from google.cloud import secretmanager
import os
import requests


def loadSecret(secret):
	try:
		GCP_PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
		if not GCP_PROJECT_ID:
			GCP_PROJECT_ID = requests.get("http://metadata.google.internal/computeMetadata/v1/project/project-id")
		name = f"projects/{GCP_PROJECT_ID}/secrets/{secret}/versions/latest"
		client = secretmanager.SecretManagerServiceClient()
		account = client.access_secret_version(request={"name":name}).payload.data.decode("UTF-8")
		return account
	except Exception as e:
		print(e)
		return None


def getSecret(secretName):
	return loadSecret(secretName)

