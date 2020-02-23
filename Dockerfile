FROM python:3.8-buster
WORKDIR /
RUN mkdir /data && apt-get update -q && apt-get install -y rrdtool && pip3 install requests speedtest-cli python-dateutil Pillow && fc-cache && apt-get clean
COPY measure.py /measure.py
CMD python3 ./measure.py
