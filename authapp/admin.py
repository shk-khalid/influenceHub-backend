from django.contrib import admin
from .models import EmailVerification
from django.core.mail import send_mail


# Admin action to verify a user
def verify_user(modeladmin, request, queryset):
    for verification in queryset:
        if not verification.is_admin_verified:
            verification.is_admin_verified = True
            verification.save()
            # Send a confirmation email to the user
            send_mail(
                'Your account has been verified',
                'Your account has been verified by an admin.',
                'no-reply@influenceHub.com',
                [verification.user.email],
                fail_silently=False,
            )
            modeladmin.message_user(request, 'User {} has been verified.'.format(verification.user.email))
        else:
            modeladmin.message_user(request, 'User {} is already verified.'.format(verification.user.email))

verify_user.short_description = 'Mark selected users as verified'

# Admin action to unverify a user
def unverify_user(modeladmin, request, queryset):
    for verification in queryset:
        if verification.is_admin_verified:
            verification.is_admin_verified = False
            verification.save()
            # Optionally, send an email to the user notifying them
            send_mail(
                'Your account has been unverified',
                'Your account has been unverified by an admin.',
                'no-reply@influenceHub.com',
                [verification.user.email],
                fail_silently=False,
            )
            modeladmin.message_user(request, 'User {} has been unverified.'.format(verification.user.email))
        else:
            modeladmin.message_user(request, 'User {} is already unverified.'.format(verification.user.email))

unverify_user.short_description = 'Unverify selected users'

# Register the EmailVerification model with custom actions
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_admin_verified', 'is_email_verified']
    actions = [verify_user, unverify_user]  # Add the actions to the admin panel

admin.site.register(EmailVerification, EmailVerificationAdmin)
