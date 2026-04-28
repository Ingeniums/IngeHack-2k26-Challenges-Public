FROM php:8.2-cli-alpine
WORKDIR /app
ENV PAYMENT_ORIGIN=http://localhost:8081 \
    BOT_SECRET=redacted-bot-secret \
    FLAG=ingehack{redacted_handout_flag}
COPY . .
EXPOSE 8000
CMD ["php", "-S", "0.0.0.0:8000", "-t", "/app"]
