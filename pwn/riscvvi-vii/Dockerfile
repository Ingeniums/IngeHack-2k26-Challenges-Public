FROM ubuntu:24.04 AS app

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -yq --no-install-recommends \
		qemu-system-misc socat \
	&& rm -rf /var/lib/apt/lists/*

RUN useradd ctf
WORKDIR /app

COPY entrypoint.sh /app/entrypoint.sh
COPY run /app/run
COPY kernel fs.img flag.txt /app/
RUN dd if=/app/flag.txt of=/app/kernel bs=1 seek=$(grep -oba "ingehack{XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX}" /app/kernel | head -n1 | cut -d: -f1) conv=notrunc
RUN rm /app/flag.txt
RUN chmod 666 /app/fs.img
RUN chmod 755 /app/run
RUN chmod 755 /app/entrypoint.sh


EXPOSE 1337

USER ctf

ENTRYPOINT [ "./entrypoint.sh" ]

