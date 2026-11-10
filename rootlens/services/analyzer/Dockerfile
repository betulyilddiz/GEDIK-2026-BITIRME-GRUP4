FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
COPY week5.py .
COPY week6.py .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
