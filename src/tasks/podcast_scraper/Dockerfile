FROM python:3.9

COPY src/tasks/podcast_scraper/src /src

WORKDIR /src

RUN python -m pip install -r requirements.txt

COPY src/db_layer/models ./db/models
COPY src/db_layer/base ./db/base

WORKDIR /

ENTRYPOINT [ "python3", "src/main.py"]
