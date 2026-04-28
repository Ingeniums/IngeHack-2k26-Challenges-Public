FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=9797
ENV DB_PATH=/data/wallet.db
ENV SESSION_SECRET=handout-session-secret
ENV FLAG=ingehack{redacted_flag}

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 120 -r requirements.txt

COPY . .

EXPOSE 9797

CMD ["python", "main.py"]
