# Use a lightweight Python base
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy app files into the container
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Streamlit environment
ENV STREAMLIT_PORT=8501
ENV STREAMLIT_ENABLE_STATIC_SERVE=true

# Run the app (case-sensitive name!)
CMD ["streamlit", "run", "Streamlit.py", "--server.port=8501", "--server.enableCORS=false"]
