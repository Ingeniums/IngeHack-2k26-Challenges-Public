FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=9797
ENV DB_PATH=/data/wallet.db
ENV SESSION_SECRET=bc38d558145bfd3ce5948ef4224a0778fb75b77c2474c17d3a6fdda8a410048e
ENV FLAG=ingehack{4s_yoU_saw_R3QueST\$_rACE_4S_gOod_a\$_C4rS}

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 120 -r requirements.txt

COPY . .

EXPOSE 9797

CMD ["python", "main.py"]
