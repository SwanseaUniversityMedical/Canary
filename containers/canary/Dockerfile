FROM alpine:3.19 as base

RUN apk update && \
    apk add --update --no-cache python3 py3-pip

COPY src/ /opt/

RUN pip3 install --user pyclean --no-cache-dir && \
    pip3 install --user -r /opt/requirements.txt --no-cache-dir && \
    rm /opt/requirements.txt && \
    pyclean -v /usr && \
    pyclean -v ~/ && \
    pip uninstall --user -y pyclean

USER root
RUN apk del py3-pip && \
    rm -rf /var/cache/apk/*

FROM scratch

COPY --from=base / /

ENTRYPOINT ["python3", "/opt/canary.py"]
#CMD ["--help"]
