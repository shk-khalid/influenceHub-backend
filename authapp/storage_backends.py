import os
import json
from datetime import timedelta
from django.core.files.storage import Storage
import firebase_admin
from firebase_admin import credentials, storage

# Load Firebase credentials from environment variable or fallback to local dev file
firebase_creds = os.environ.get('FIREBASE_CREDENTIALS')
if firebase_creds:
    cred_dict = json.loads(firebase_creds)
    cred = credentials.Certificate(cred_dict)
else:
    cred_path = os.path.join(os.path.dirname(__file__), 'firebase_credentials.json')
    cred = credentials.Certificate(cred_path)

# Initialize Firebase Admin SDK only once
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'storageBucket': "influencehub-9955b.appspot.com"  # Correct domain is .app**spot**.com
    })

class FirebaseStorage(Storage):
    def _open(self, name, mode='rb'):
        raise NotImplementedError("This backend doesn't support opening files directly.")

    def _save(self, name, content):
        bucket = storage.bucket()
        blob = bucket.blob(name)
        blob.upload_from_file(content.file, content_type=content.content_type)
        return name

    def exists(self, name):
        bucket = storage.bucket()
        blob = bucket.blob(name)
        return blob.exists()

    def url(self, name):
        bucket = storage.bucket()
        blob = bucket.blob(name)
        return blob.generate_signed_url(timedelta(hours=1))

    def deconstruct(self):
        return ("authapp.storage_backends.FirebaseStorage", [], {})
