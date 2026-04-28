FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=9696
ENV SESSION_SECRET=ffc34b81775ea2a02736b0f525b9cb16c36f6bfe6a72ed4d997f8cf9f524c013
ENV FLAG=ingehack{y3aH_1T_was_4\$_\$1MPL3_As_YOU_TH0uGhT}

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 9696

CMD ["python", "main.py"]
