FROM alpine:3.20 as base

COPY src/ /opt/

RUN apk update && \
    apk add --update --no-cache python3 py3-pip && \
    pip install --break-system-packages pyclean --no-cache-dir && \
    pip install --break-system-packages -r /opt/requirements.txt --no-cache-dir && \
    rm /opt/requirements.txt && \
    pyclean -v /usr && \
    pyclean -v ~/ && \
    pip uninstall --break-system-packages -y pyclean && \
    apk del py3-pip && \
    rm -rf /var/cache/apk/*

FROM scratch
COPY --from=base / /

ENTRYPOINT ["python3", "/opt/canary.py"]
#CMD ["--help"]
