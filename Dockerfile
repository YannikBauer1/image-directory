FROM python:3.8

ENV GOOGLE_CLOUD_PROJECT bdccproject01

WORKDIR /firstdocker

COPY ./app/requirements.txt .

RUN pip3 install -r requirements.txt

COPY ./app ./app

CMD ["python", "./app/main.py"]

