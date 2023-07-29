#!/bin/sh
celery -A pdf_task.pdf_app worker --pool=solo --loglevel=info