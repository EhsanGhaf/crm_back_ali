from django.db import models
import pyotp
from django.contrib.auth.models import User, AbstractUser


# Create your models here.

class User(AbstractUser):
    zammad_id = models.IntegerField(blank=True, null=True,verbose_name='آیدی معادل زمد')

    is_2fa_enabled = models.BooleanField(default=False)
    otp_base32 = models.CharField(max_length=32, null=True, blank=True)

    def generate_otp_secret(self):
        self.otp_base32 = pyotp.random_base32()
        self.save()

    def verify_otp(self, token):
        if not self.otp_base32:
            return False
        totp = pyotp.TOTP(self.otp_base32)
        return totp.verify(token)

    def __str__(self):
        return f"پروفایل {self.user.username}"

class Team(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='نام تیم')
    description = models.TextField(blank=True,null=True,verbose_name='توضیحات')
    is_active = models.BooleanField(default=True,verbose_name='فعال')

    members = models.ManyToManyField(
        User,
        blank=True,
        related_name='teams',
        verbose_name='اعضای تیم'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'تیم / کارتابل'
        verbose_name_plural = 'تیم ها و کارتابل ها'

    def __str__(self):
        return self.name