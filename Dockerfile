FROM python:3
USER root

RUN apt-get update
RUN apt-get -y install ffmpeg poppler-utils
ENV TERM xterm

ENV PYTHONDONTWRITEBYTECODE 1
RUN pip install unidecode pillow pybtex pikepdf nltk

WORKDIR /root
ENTRYPOINT ["/usr/local/bin/python3","-u","main.py"]