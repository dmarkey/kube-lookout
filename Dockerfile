FROM alpine:3.13
ADD requirements.txt /tmp
RUN apk update &&  apk add libffi openssl py3-pip && apk add gcc musl-dev python3-dev libffi-dev openssl-dev && pip3 install wheel && pip3 install -r /tmp/requirements.txt  && apk del openssl-dev libffi-dev python3-dev musl-dev gcc && rm -f /var/cache/apk/*
ADD lookout.py /root
ENTRYPOINT  ["python3", "-u", "/root/lookout.py"]
