FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 7047
ENV PORT=7047
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:7047", "--workers", "1", "--threads", "4", "--timeout", "120"]
