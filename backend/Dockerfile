FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies directly
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app.py"]
