from django.db import models

# Create your models here.
class Template(models.Model):
    name = models.CharField(max_length=100)
    folder = models.CharField(max_length=100)

    def __str__(self):
        return self.name