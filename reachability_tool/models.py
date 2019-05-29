import os
from datetime import timedelta
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

# Create your models here.
class Device(models.Model):
    states_list = (
        ('2', 'Fail'),
        ('1', 'OK'),
        ('0', 'Alert'),
    )
    ticket = models.CharField(max_length=100)
    reporter = models.CharField(max_length=100)
    state = models.CharField(max_length=1, choices=states_list)
    ip = models.GenericIPAddressField('IP', unique=True)
    target = models.DateTimeField(default=timezone.now() + timedelta(42))

    def test_connectibity(self):
        now = timezone.now()
        not_passed = os.system('ping -c 1 %s' % (self.ip))
        if not not_passed and now >= self.target:
            self.state = 0 #alert
            self.save()
            return False
        elif not_passed:
            self.state = 2  # alert
            self.save()
        elif not not_passed:
            self.state = 1  # alert
            self.save()
        return True

    def __str__(self):
        return self.ip
