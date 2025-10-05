FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# ffmpeg must be installed
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
ENV FLASK_APP=app.py
EXPOSE 5000
CMD ["python", "app.py"]
