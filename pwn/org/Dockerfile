FROM ubuntu:24.04 AS app

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -yq --no-install-recommends \
        socat \
    && rm -rf /var/lib/apt/lists/*

RUN useradd ctf
WORKDIR /app

COPY entrypoint.sh /app/entrypoint.sh
COPY flag.txt /app/flag.txt
COPY chall /app/chall

RUN chmod 666 /app/flag.txt \
    && chmod 755 /app/entrypoint.sh /app/chall

EXPOSE 1337

USER ctf

ENTRYPOINT ["./entrypoint.sh"]
