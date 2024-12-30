from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.utils import timezone
import random
import time
import uuid
import string

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser):
    
    NICHE_CHOICES = [
        ('technology', 'Technology'),
        ('fashion', 'Fashion & Beauty'),
        ('fitness', 'Fitness and Health'),
        ('food', 'Food and Cooking'),
        ('travel', 'Travel'),
        ('gaming', 'Gaming'),

    ]
    
    username = models.CharField(unique=True, max_length=255, null=True, blank=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    fullName = models.CharField(max_length=255, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    socialLinks = models.JSONField(null=True, blank=True)
    profilePicture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    niche = models.CharField(max_length=50, choices=NICHE_CHOICES, default=None, null=True, blank=True)
    languages = models.JSONField(default=list, blank=True)
    collaborate = models.BooleanField(default=False)

    # status flags
    is_email_verified = models.BooleanField(default=False)
    is_admin_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return self.username

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        return self.is_superuser

    def has_module_perms(self, app_label):
        "Does the user have permissions for the given app?"
        return self.is_superuser
    
    def generate_username(self, email):
        username = email.split('@')[0]
        
        while User.objects.filter(username=username).exists():
            random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            username = "{}_{}".format(username, random_str)
        
        return username
    
    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.generate_username(self.email)
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = "users"

class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    timestamp = models.DateTimeField(auto_now_add=True)

    def generate_otp(self):
        self.code = str(random.randint(100000, 999999))
        self.save()
        return self.code

    def is_expired(self):
        # Validity set for 3 minutes
        return (time.time() - self.timestamp.timestamp()) > 180

class EmailVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    is_email_verified = models.BooleanField(default=False)
    is_admin_verified = models.BooleanField(default=False) 

    def generate_token(self):
        # Generate and return verification token
        self.token = uuid.uuid4()
        self.save()
        return self.token

class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    timestamp = models.DateTimeField(auto_now_add=True)

    def generate_otp(self):
        self.code = str(random.randint(100000, 999999))
        self.save()
        return self.code

    def is_expired(self):
        # Validity set for 3 minutes
        return (time.time() - self.timestamp.timestamp()) > 180
