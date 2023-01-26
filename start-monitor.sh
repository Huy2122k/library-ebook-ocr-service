#!/bin/sh
pip install requests
pip install gTTS
pip install pydub
celery -A pdf_task.pdf_app flower --address=127.0.0.1 --port=5566 --broker=amqp://admin:mypass@rabbit:5672