FROM python:3
USER root

RUN apt-get update
RUN apt-get -y install ffmpeg poppler-utils nodejs npm
ENV TERM xterm

ENV PYTHONDONTWRITEBYTECODE 1
RUN pip install unidecode pillow pybtex pikepdf nltk latexcodec psutil

WORKDIR /install
RUN npm install express moment winston winston-daily-rotate-file serve-index

WORKDIR /root
ENV NODE_PATH=/install/node_modules
ENTRYPOINT ["/usr/local/bin/python3","-u","main.py"]