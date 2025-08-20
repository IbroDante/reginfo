# celery_worker.py
from celery import Celery
from app import app

celery = Celery(app.import_name, broker=app.config["REDIS_URL"])
celery.conf.update(app.config)
