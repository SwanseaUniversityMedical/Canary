FROM alpine:3.18

COPY src/ /opt/

RUN apk update && apk add --update --no-cache \
	python3 \
    py3-pip && \
    pip install pyclean --no-cache-dir && \
    pip install -r /opt/requirements.txt --no-cache-dir && \
    rm /opt/requirements.txt && \
    pyclean -v /usr && \
    pip uninstall -y pyclean && \
    apk del py3-pip && \
    rm -rf /var/cache/apk/*

ENTRYPOINT ["python3", "/opt/canary.py"]
#CMD ["--help"]