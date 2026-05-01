FROM python:3.9-slim
WORKDIR /app

# Install system dependencies for voice and audio
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Copy everything (app.py, logo.png, jain_vault, etc.)
COPY . .

# Ensure your vault folder exists with correct permissions
RUN mkdir -p jain_vault && chmod 777 jain_vault

RUN pip install -r requirements.txt

EXPOSE 8080

# Run with 10GB upload limit enabled
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.maxUploadSize=10240"]