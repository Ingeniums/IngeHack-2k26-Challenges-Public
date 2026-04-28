FROM sagemath/sagemath:latest

USER root
RUN apt-get update && apt-get install -y socat
RUN sage -pip install pycryptodome
RUN which sage
RUN ls -la $(which sage)

WORKDIR /app
COPY src/chall.py .
COPY flag.txt .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh
RUN chown -R root:root /app && chmod -R 555 /app

EXPOSE 4000
ENTRYPOINT ["./entrypoint.sh"]
