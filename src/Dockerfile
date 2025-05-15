FROM python:3.12.9-slim-bookworm

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source code and config
COPY src ./src

# Run from inside /app/src
WORKDIR /app/src

CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]

# Use Python 3.12 slim image
# FROM python:3.12.9-slim-bookworm

# # Set working directory
# WORKDIR /app

# # Install system dependencies required for PyAudio
# RUN apt-get update && apt-get install -y \
#     build-essential \
#     portaudio19-dev \
#     libasound2-dev \
#     libjack-jackd2-dev \
#     ffmpeg \
#     && rm -rf /var/lib/apt/lists/*

# # Copy and install Python dependencies
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy all source code and config
# COPY src ./src

# # Run from inside /app/src
# WORKDIR /app/src

# # Start Streamlit app
# CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
