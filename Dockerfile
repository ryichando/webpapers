FROM python:3
USER root

RUN apt-get update
RUN apt-get -y install ffmpeg poppler-utils
ENV TERM xterm

COPY requirements.txt /root
WORKDIR /root

RUN pip install --upgrade pip
RUN pip install --upgrade setuptools
RUN pip install -r requirements.txt
