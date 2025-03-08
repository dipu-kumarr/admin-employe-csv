from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import Group, Permission
from django.utils.timezone import now
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
import threading
import time
import datetime
class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('employee', 'Employee'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    # groups = models.ManyToManyField(Group, related_name="custom_user_groups", blank=True)
    # user_permissions = models.ManyToManyField(Permission, related_name="custom_user_permissions", blank=True)
    def __str__(self):
        return f"{self.username} ({self.role})"

class Record(models.Model):
    employee = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def schedule_deletion(self):
        """Schedule record deletion after 10 minutes"""
        def delete_record(record_id):
            time.sleep(600)  # Wait for 10 minutes
            Record.objects.filter(id=record_id).delete()  # Avoid using `self` after thread sleep

        threading.Thread(target=delete_record, args=(self.id,)).start()