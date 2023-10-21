FROM python:3.12.0-alpine3.18

COPY src/ /opt/

RUN pip install pyclean --no-cache-dir && \
    pip install -r /opt/requirements.txt --no-cache-dir && \
    rm /opt/requirements.txt && \
    pyclean -v /usr && \
    pip uninstall -y pyclean && \
    apk del py3-pip && \
    rm -rf /var/cache/apk/*

ENTRYPOINT ["python3", "/opt/canary.py"]
#CMD ["--help"]
