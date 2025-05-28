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
