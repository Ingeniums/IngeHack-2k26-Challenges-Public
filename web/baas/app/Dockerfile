FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=9898
ENV SESSION_SECRET=4ae7f560ec5eb4692fe7f4ca5fdc7f4d6f56f4fe5783b62d3ad8750607e47562
ENV FLAG=ingehack{l0c4lh0st_1s_st1ll_4_pl4c3_y0u_c4n_br0ws3}
ENV INTERNAL_FETCH_TOKEN=baas-internal-fetch-token

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 9898

CMD ["python", "main.py"]
