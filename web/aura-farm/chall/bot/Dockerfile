FROM node:20-bookworm-slim

WORKDIR /app

ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 \
    BOT_PORT=8082 \
    BOT_TIMEOUT_MS=15000 \
    BOT_NAVIGATION_WAIT_UNTIL=domcontentloaded \
    BOT_APP_ORIGIN=http://localhost:8090 \
    BOT_SECRET=redacted-bot-secret

COPY package.json ./
RUN npm install --omit=dev \
    && npx playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

COPY . .

EXPOSE 8082

CMD ["npm", "start"]
