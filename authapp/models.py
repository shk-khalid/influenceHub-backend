from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.utils import timezone
from datetime import timedelta
import random
import string

class UserManager(BaseUserManager):
    def create_user(self, email, username=None, password=None, **extra_fields):
        if not email:
            raise ValueError('The email must be set')
        
        email = self.normalize_email(email)
        if not username:
            username = self.generate_unique_username(email)

        extra_fields.pop('username', None)  # Prevent duplicate username key

        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if not extra_fields.get('username'):
            extra_fields['username'] = self.generate_unique_username(email)

        return self.create_user(email, password, **extra_fields)
    
    def generate_unique_username(self, email):
        base_username = email.split('@')[0]
        username = base_username

        while User.objects.filter(username=username).exists():
            random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            username = f"{base_username}_{random_str}"

        return username

class User(AbstractBaseUser):
    
    NICHE_CHOICES = [
        ('technology', 'Technology'),
        ('fashion', 'Fashion & Beauty'),
        ('fitness', 'Fitness and Health'),
        ('food', 'Food and Cooking'),
        ('travel', 'Travel'),
        ('gaming', 'Gaming'),
    ]
    
    email = models.EmailField(unique=True)
    userName = models.CharField(unique=True, max_length=255)
    password = models.CharField(max_length=255)
    fullName = models.CharField(max_length=255, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    socialLinks = models.JSONField(null=True, blank=True)
    profilePicture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    niche = models.CharField(max_length=50, choices=NICHE_CHOICES, null=True, blank=True)
    languages = models.JSONField(default=list, blank=True)
    collaborate = models.BooleanField(default=False)

    # Status flags
    is_admin_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'  # Changed to 'email' for better authentication handling
    REQUIRED_FIELDS = ['userName']

    def __str__(self):
        return self.userName

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser

    class Meta:
        db_table = "users"

class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    timestamp = models.DateTimeField(auto_now_add=True)
    expired = models.BooleanField(default=False)

    def generate_otp(self):
        self.code = str(random.randint(100000, 999999))
        self.expired = False
        self.save()
        return self.code

    def is_expired(self):
        return timezone.now() > (self.timestamp + timedelta(minutes=3))