#!/bin/sh
celery -A pdf_task.pdf_app flower --broker=amqp://admin:mypass@rabbit:5672