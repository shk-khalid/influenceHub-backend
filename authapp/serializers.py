from rest_framework import serializers
from .models import User, InstaPost, InstaStats
import json

class UserSerializer(serializers.ModelSerializer):
    profilePicture = serializers.ImageField(use_url=True, required=False)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'fullName', 'location', 'bio', 
            'socialLinks', 'profilePicture', 'niche', 'languages',
        ]
        
class RegistrationSerializer(serializers.ModelSerializer):
    password_confirmation = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirmation']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirmation']:
            raise serializers.ValidationError("Password must watch.")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirmation')
        user = User.objects.create_user(**validated_data)
        return user

    
class LoginSerializer(serializers.Serializer):
    email_or_username = serializers.CharField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        username_or_email = attrs.get('email_or_username')
        password = attrs.get('password')
        
        if '@' in username_or_email:
            user = User.objects.filter(email=username_or_email).first()
        else:
            user = User.objects.filter(userName=username_or_email).first()
            
        if not user:
            raise serializers.ValidationError('Invalid credentials')
        
        if not user.check_password(password):
            raise serializers.ValidationError('Invalid credentials')
        
        attrs['user'] = user 
        return attrs

class ProfileUpdateSerializer(serializers.ModelSerializer):
    languages = serializers.ListField(child=serializers.DictField(), required=False)
    profilePicture = serializers.ImageField(use_url=True, required=False)

    class Meta: 
        model = User 
        fields = [
            'username', 'fullName', 'location', 'bio',
            'socialLinks', 'profilePicture', 'niche', 'languages'
        ]

    def to_internal_value(self, data):
        if 'socialLinks' in data and isinstance(data['socialLinks'], str):
            try:
                data['socialLinks'] = json.loads(data['socialLinks'])
            except Exception:
                raise serializers.ValidationError({"socialLinks": "Invalid JSON format for socialLinks."})
        if 'languages' in data and isinstance(data['languages'], str):
            try:
                data['languages'] = json.loads(data['languages'])
            except Exception:
                raise serializers.ValidationError({"languages": "Invalid JSON format for languages."})
        return super().to_internal_value(data)

    def validate_languages(self, value):
        valid_languages = {
            'English', 'Spanish', 'French', 'German', 'Italian', 'Portuguese',
            'Chinese', 'Japanese', 'Korean', 'Russian', 'Arabic', 'Hindi'
        }
        valid_levels = {'Native', 'Fluent', 'Advanced', 'Intermediate', 'Basic'}

        if not isinstance(value, list):
            raise serializers.ValidationError("Languages must be provided as a list.")

        for lang in value:
            if not isinstance(lang, dict):
                raise serializers.ValidationError("Each language must be a dictionary.")
            
            name = lang.get('name')
            level = lang.get('level')

            if not name or not level:
                raise serializers.ValidationError("Each language entry must contain 'name' and 'level'.")
            
            if name not in valid_languages:
                raise serializers.ValidationError(
                    f"Invalid language: {name}. Must be one of {', '.join(valid_languages)}."
                )
            if level not in valid_levels:
                raise serializers.ValidationError(
                    f"Invalid level for {name}: {level}. Must be one of {', '.join(valid_levels)}."
                )
        return value

    def update(self, instance, validated_data):
        languages_data = validated_data.pop('languages', None)
        
        for field, value in validated_data.items():
            setattr(instance, field, value)
        
        if languages_data is not None:
            instance.languages = languages_data
        
        instance.save() 
        return instance
   
class InstaPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstaPost
        fields = [
            'post_number', 'post_detail'
        ]

class InstaStatsSerializer(serializers.ModelSerializer):
    posts = InstaPostSerializer(many=True, required=False)

    class Meta:
        model = InstaStats
        fields = [
            'insta_id', 'userName', 'bio', 'category', 
            'is_verified', 'is_professional', 'followers', 
            'following', 'posts_count', 'posts'
        ]

    def create(self, validated_data):
        posts_data = validated_data.pop('posts', [])
        insta_stats = InstaStats.objects.create(**validated_data)

        for post_data in posts_data:
            InstaPost.objects.create(insta_stats=insta_stats, **post_data)
        return insta_stats
    
    def update(self, instance, validated_data):
        posts_data = validated_data.pop('posts', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if posts_data is not None:
            # Option: Clear out all existing posts and add the new ones.
            instance.posts.all().delete()
            for post_data in posts_data:
                InstaPost.objects.create(insta_stats=instance, **post_data)
                
        return instance