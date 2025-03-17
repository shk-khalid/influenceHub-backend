from django.core.files.storage import Storage
from datetime import timedelta
import firebase_admin
from firebase_admin import credentials, storage

# Initialize Firebase Admin SDK (this runs once)
if not firebase_admin._apps:
    cred = credentials.Certificate(r"authapp\firebase_credentials.json")
    firebase_admin.initialize_app(cred, {
        'storageBucket': "influencehub-9955b.firebasestorage.app"
    })    

class FirebaseStorage(Storage):
    def _open(self, name, mode='rb'):
        # Reading files directly from Firebase is not implemented.
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
        # Generate a signed URL valid for 1 hour.
        return blob.generate_signed_url(timedelta(hours=1))

    def deconstruct(self):
        """
        Return enough information to recreate the storage backend.
        Since no additional parameters are used, we simply return the full
        python path of the class with empty args and kwargs.
        """
        return ("authapp.storage_backends.FirebaseStorage", [], {})   