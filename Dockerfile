FROM python:3.8-slim-buster

ENV TZ 'America/Sao_Paulo'

RUN apt-get update -y && \
    apt-get install -y python-pip python-dev

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install -r requirements.txt

COPY . /app

COPY ./.env /app

ENTRYPOINT [ "python" ]

CMD [ "run.py" ]