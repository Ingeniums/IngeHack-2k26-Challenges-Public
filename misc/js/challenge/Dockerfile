FROM node:18-alpine

RUN apk add --no-cache su-exec
RUN addgroup -S ctf && adduser -S ctf -G ctf

WORKDIR /app

COPY package.json ./
RUN npm install --omit=dev

COPY server.js entrypoint.sh flag.txt ./

RUN chmod +x /app/entrypoint.sh \
    && chmod -R a+rX /app

ENV PORT=3000
EXPOSE 3000

ENTRYPOINT ["/app/entrypoint.sh"]
