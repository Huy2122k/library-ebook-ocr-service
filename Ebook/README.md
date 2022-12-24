# Using Ebook to main folder

```
cd Ebook
```

# Install

## Python env (options)

```
python3 -m venv yourenvpath
source yourenvpath/bin/activate
```

## Library

```
pip install -r requirements.txt
```

## env

config your .env and cloud/env.cloud

## addition

- mongodb + ffmpeg
- todo: use docker instead

# How to run

service

- in root folder run this command to startup minio + redis + rabbitmq

```
docker compose up -d
```

workers

```
celery -A pdf_task.pdf_app worker --pool=solo --loglevel=info
celery -A pdf_task.pdf_app flower --address=127.0.0.6 --port=5566 --broker=amqp://admin:mypass@localhost:5672
```

server

```
python run.py
```
