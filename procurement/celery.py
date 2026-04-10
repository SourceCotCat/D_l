import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'procurement.settings')

app = Celery('procurement')

# загружаем конфигурацию из settings.py — все ключи с префиксом CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# автоматически находим tasks.py во всех INSTALLED_APPS
app.autodiscover_tasks()
