FROM python:3.7
LABEL maintainer="jmmshn@lbl.gov"

RUN mkdir -p /home/project/dash_app
WORKDIR /home/project/dash_app

RUN pip install --no-cache-dir numpy scipy

ADD requirements.txt /home/project/dash_app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

ENV DASH_NUM_WORKERS=1

ADD . /home/project/dash_app

EXPOSE 8000
CMD gunicorn --workers=$DASH_NUM_WORKERS --timeout=300 --bind=0.0.0.0 app:server
