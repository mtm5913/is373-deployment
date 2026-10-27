FROM python:3.13-alpine
WORKDIR /app
COPY etl /app/etl
RUN adduser -D -u 10001 etl
USER etl
ENTRYPOINT ["python", "-m", "etl.pipeline"]
