FROM alpine:3.19 as base

RUN apk update && \
    apk add --update --no-cache python3 py3-pip

COPY src/ /opt/
RUN adduser -D -u 1002 -g '' canary root
USER canary

RUN pip3 install pyclean --no-cache-dir && \
    pip3 install -r /opt/requirements.txt --no-cache-dir && \
    rm /opt/requirements.txt && \
    pyclean -v /usr && \
    pyclean -v ~/ && \
    pip uninstall -y pyclean

USER root
RUN apk del py3-pip && \
    rm -rf /var/cache/apk/*

FROM scratch
COPY --from=base / /
RUN adduser -D -u 1002 -g '' canary root
USER canary

ENTRYPOINT ["python3", "/opt/canary.py"]
#CMD ["--help"]
