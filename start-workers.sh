#!/bin/sh
pip install requests
pip install gTTS
pip install pydub
celery -A pdf_task.pdf_app worker --pool=solo --loglevel=info