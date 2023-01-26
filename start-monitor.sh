#!/bin/sh
pip install requests
pip install gTTS
pip install pydub
celery -A pdf_task.pdf_app flower --broker=amqp://admin:mypass@rabbit:5672