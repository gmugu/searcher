FROM python:3.9-alpine

COPY rootfs /

RUN set -evu; \
    pip install aiohttp beautifulsoup4; \
    apk add --no-cache bash tzdata; \
    chmod +x /entrypoint.sh;

WORKDIR /app/
EXPOSE 9094
CMD [ "/entrypoint.sh" ]