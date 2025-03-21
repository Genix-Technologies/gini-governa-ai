# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for PyAudio, FFmpeg, and other libraries
RUN apt-get update && apt-get install -y \
    python3-pyaudio \
    portaudio19-dev \
    libportaudio2 \
    libportaudiocpp0 \
    ffmpeg \
    libavcodec-extra \
    build-essential \
    python3-dev \
    && apt-get clean

# Copy requirements file to the container
COPY requirements.txt /app/requirements.txt

# Upgrade pip and install required packages
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application files
COPY . /app

# Expose Flask and Streamlit ports
EXPOSE 5000 8501

# Run Flask app (Streamlit will be spawned automatically)
CMD ["python", "flask_app.py"]
