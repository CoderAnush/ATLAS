FROM python:3.11-slim
COPY infrastructure/docker/bin/mc /usr/local/bin/mc
RUN chmod +x /usr/local/bin/mc
ENTRYPOINT ["mc"]
