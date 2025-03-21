# Use the official Python image
FROM python:3.11-slim

# Set the working directory
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

# Add --trusted-host to avoid SSL errors (optional if SSL issues persist)
RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host pypi.python.org \
    --trusted-host files.pythonhosted.org \
    -r /app/requirements.txt

# Copy application files
COPY . /app

# Expose the port for Streamlit
EXPOSE 8501

# Run the application
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
