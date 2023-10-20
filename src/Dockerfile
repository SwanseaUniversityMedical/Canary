FROM alpine:3.18

COPY requirements.txt .
COPY main.py .

RUN apk update && apk add --update --no-cache \
	python3 \
	py3-pip && \
	ln -sf python3 /usr/bin/python # Makes 'python' available in path

RUN pip install -r /requirements.txt --no-cache-dir && \
    rm /requirements.txt

ENTRYPOINT ["python", "/main.py"]
#CMD ["--help"]