# Use official Python image as a base
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install necessary system dependencies
RUN apt-get update && apt-get install -y \
    python3-pyaudio \
    portaudio19-dev \
    libportaudio2 \
    libportaudiocpp0 \
    ffmpeg \
    libavcodec-extra \
    build-essential \
    python3-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements file to container
COPY requirements.txt /app/requirements.txt

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host pypi.python.org \
    --trusted-host files.pythonhosted.org \
    -r /app/requirements.txt

# Copy the application code to the container
COPY . /app

# Expose Flask port (8021)
EXPOSE 8501

# Set Flask app environment variable (main file is flask_app.py)
ENV FLASK_APP=flask_app.py

# Run Flask application on port 8021
CMD ["flask", "run", "--host=0.0.0.0", "--port=8501"]
