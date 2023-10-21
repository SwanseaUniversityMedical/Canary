FROM python:3.11.6-alpine3.18 as base
COPY src/requirements.txt /requirements.txt

RUN apk update && \
    apk add --update --no-cache \
	python3 \
        py3-pip \
	alpine-sdk
    
RUN mkdir -p /wheels && \
    pip wheel -w /wheels -r requirements.txt
    
FROM python:3.11.6-alpine3.18 as expanded
COPY src/ /opt/
COPY --from=base /wheels /wheels

RUN pip install pyclean --no-cache-dir && \
    pip install /wheels/* --no-cache-dir && \
    rm -rf /wheels && \
    pyclean -v /usr && \
    pip uninstall -y pyclean && \
    rm -rf /var/cache/apk/* && \
    rm -rf /tmp/*

FROM scratch
COPY --from=expanded / /

ENTRYPOINT ["python3", "/opt/canary.py"]
#CMD ["--help"]
