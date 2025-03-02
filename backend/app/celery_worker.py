from celery import Celery
import requests
import os
from dotenv import load_dotenv

load_dotenv()

celery_app = Celery(
    "tasks",
    broker=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://redis:6379/0"),
)

SPLEETER_API_URL = "http://spleeter:5001/separate/"

@celery_app.task
def process_file(file_name):
    try:
        response = requests.post(SPLEETER_API_URL, json={"file_name": file_name})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}
