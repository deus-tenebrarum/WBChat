from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    department = models.CharField(max_length=100, blank=True)  # отдел
    avatar = models.ImageField(upload_to='', blank=True, null=True)
    isModerator = models.BooleanField(default=False)
    def __str__(self):
        return self.username
