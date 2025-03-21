from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.utils import timezone
from datetime import timedelta
import random, string
from .storage_backends import FirebaseStorage
from django.conf import settings
from brands_insightapp.models import Brand


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
    profilePicture = models.ImageField(
        storage=FirebaseStorage(),
        upload_to='profile_pics/',
        null=True,
        blank=True,
    )
    username = models.CharField(unique=True, max_length=255)
    password = models.CharField(max_length=255)
    fullName = models.CharField(max_length=255, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    socialLinks = models.JSONField(null=True, blank=True)
    niche = models.CharField(max_length=50, choices=NICHE_CHOICES, null=True, blank=True)
    languages = models.JSONField(default=list, blank=True)

    # Status flags
    is_admin_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'  # Changed to 'email' for better authentication handling
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.username

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
    

class InstaStats(models.Model):
    insta_id = models.CharField(max_length=100, unique=True)
    userName = models.CharField(max_length=255)
    bio = models.TextField(null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    is_professional = models.BooleanField(default=False)
    followers = models.PositiveIntegerField(default=0)
    following = models.PositiveIntegerField(default=0)
    posts_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.userName
    
class InstaPost(models.Model):
    insta_stats = models.ForeignKey(InstaStats, on_delete=models.CASCADE, related_name="posts")
    post_number = models.PositiveIntegerField() # value from 1 to 12
    post_detail = models.JSONField()

    def __str__(self):
        return f"Post {self.post_number} of {self.insta_stats.userName}"
    
def create_insta_posts(insta_stats, posts_data):
    for i in range(1, 13):
        post_detail = posts_data[i-1] if i-1 < len(posts_data) else {}
        InstaPost.objects.create(insta_stats=insta_stats, post_number=i, post_detail=post_detail) 

class BrandSuggestion(models.Model):
    DECISION_CHOICES = [
        ("accepted", "Accepted"),
        ("declined", 'Declined'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="brand_suggestions")
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    decision = models.CharField(max_length=15, choices=DECISION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.brand.name} ({self.decision})"