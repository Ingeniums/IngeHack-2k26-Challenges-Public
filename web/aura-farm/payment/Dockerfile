FROM php:8.2-cli-alpine
WORKDIR /app
ENV APP_ORIGIN=http://localhost:8090
COPY . .
EXPOSE 8000
CMD ["php", "-S", "0.0.0.0:8000", "-t", "/app"]
