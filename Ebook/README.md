<h1 align="center"> Flask-CRUD-REST-API </h1>

> <h2 align="center"> Flask based CRUD REST API for Movies using Flask-Restful and MongoDB </h2>

docker compose -f jobs/queue.yml up -d

celery -A pdf_task.pdf_app worker --pool=solo --loglevel=info
