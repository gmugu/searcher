FROM python:3.9-alpine

COPY rootfs /

RUN set -evu; \
    pip install aiohttp; \
    chmod +x /entrypoint.sh;

WORKDIR /app/
EXPOSE 9094
CMD [ "/entrypoint.sh" ]