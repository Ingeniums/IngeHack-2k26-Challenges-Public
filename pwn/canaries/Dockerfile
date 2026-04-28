FROM ubuntu:24.04 AS app

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -yq --no-install-recommends \
		socat \
	&& rm -rf /var/lib/apt/lists/*

RUN useradd ctf
WORKDIR /app

COPY entrypoint.sh /app/entrypoint.sh
COPY run.sh /app/run
COPY main /app/main
COPY flag.txt /app/flag.txt

RUN chmod 755 /app/entrypoint.sh /app/run /app/main

EXPOSE 6702

USER ctf

ENTRYPOINT [ "./entrypoint.sh" ]
