FROM ubuntu:latest

COPY . /source 

WORKDIR /source/Ebook
# RUN add-apt-repository universe
RUN cat requirements.txt
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get install -y \
    software-properties-common
RUN add-apt-repository universe
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt update
RUN apt-get -y install python3.8  \
    python3-pip
    
RUN cd /source/Ebook & pip install -r requirements.txt
####
# for audio processing
RUN apt-get -y install ffmpeg 
###
RUN apt-get -y install tesseract-ocr 
RUN apt-get -y install libtesseract-dev
