FROM python:3.7-slim-stretch

WORKDIR /app
COPY . ./

RUN pip install pipenv \
	&& pipenv install --system --deploy \
        && rm -rf /var/lib/apt/lists/*

USER nobody
ENTRYPOINT  [ "python", "/app/lookout.py" ]
CMD [ "--config=/etc/kube-lookout/config.yml "]
