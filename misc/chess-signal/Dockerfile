FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY ./challenge/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./challenge ./

EXPOSE 8000

CMD ["python", "app.py"]
