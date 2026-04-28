FROM php:8.2-cli-alpine
WORKDIR /app
ENV PAYMENT_ORIGIN=http://localhost:8081 \
    BOT_SECRET=f9a585d5d3c90ac6a4ad6c23bea450718b3707c59aba45089189e6ca3edc2654 \
    FLAG=ingehack{hTTP_S3cUr1tY_HE4D3rS_GO_bRRrrRrrRRrr}
COPY . .
EXPOSE 8000
CMD ["php", "-S", "0.0.0.0:8000", "-t", "/app"]
