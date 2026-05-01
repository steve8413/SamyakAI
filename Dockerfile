FROM python:3.9-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

COPY . .

# THIS LINE FIXES IT: It creates the folder if it's missing
RUN mkdir -p jain_vault && chmod 777 jain_vault

RUN pip install -r requirements.txt

EXPOSE 8080

CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.maxUploadSize=10240"]
