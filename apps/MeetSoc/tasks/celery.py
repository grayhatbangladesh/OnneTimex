import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "DevazBackend.settings")

app = Celery("meetsoc")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(["celery_tasks"])
