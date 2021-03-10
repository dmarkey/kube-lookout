FROM alpine:3.13
ADD requirements.txt /tmp
RUN apk update &&  apk add libffi openssl python3 py3-pip && apk add gcc musl-dev python3-dev libffi-dev openssl-dev && pip install pip==21.0.1 --upgrade && pip install wheel==0.36.2 && pip3 install -r /tmp/requirements.txt --ignore-installed six  && apk del openssl-dev libffi-dev python3-dev musl-dev gcc && rm -f /var/cache/apk/*
ADD lookout.py /root
ENTRYPOINT  ["python3", "-u", "/root/lookout.py"]
