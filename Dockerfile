FROM python:3.7
LABEL maintainer="jmmshn@lbl.gov"

RUN mkdir -p /home/project/dash_app
RUN mkdir -p /home/project/dash_app/secrets

WORKDIR /home/project/dash_app

ADD requirements.txt /home/project/dash_app/requirements.txt
ADD ./secrets/db_info.json /home/project/dash_app/secrets/db_info.json

RUN pip install --no-cache-dir -r requirements.txt

# Dash callbacks are blocking, and also often network-limited
# rather than CPU-limited, so using NUM_WORKERS >> number of
# CPU cores is sensible

ADD . /home/project/dash_app
EXPOSE 8000
CMD gunicorn --workers=16 --timeout=300 --bind=0.0.0.0 app:server
