FROM python:3.11-slim
WORKDIR /app

COPY services/web/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY services/web/start.sh ./start.sh
RUN chmod +x ./start.sh
RUN mkdir -p /app/data

EXPOSE 8000
CMD ["./start.sh"]
