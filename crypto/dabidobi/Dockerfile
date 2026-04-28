FROM python:3.11-slim

# Install socat
RUN apt-get update && apt-get install -y socat && rm -rf /var/lib/apt/lists/*

# Install crypto dependency
RUN pip install --no-cache-dir pycryptodome

# Create app directory
WORKDIR /app

# Copy files
COPY /src/chall.py .
COPY flag.txt .
COPY entrypoint.sh .

# Permissions (read-only challenge)
RUN chmod +x entrypoint.sh && \
    chown -R root:root /app && \
    chmod -R 555 /app

# Expose port
EXPOSE 4000

# Run
ENTRYPOINT ["./entrypoint.sh"]
