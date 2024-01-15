# Use an official Python runtime as a parent image
FROM python:3.12

# Set the working directory to /app
WORKDIR /app

# Install PyQt5 and required dependencies
RUN apt-get update && apt-get install -y python3-pyqt5 pyqt5-dev-tools xvfb

# Copy the current directory contents into the container at /app
COPY . /app

# Start Xvfb
CMD ["Xvfb", ":0", "-screen", "0", "1920x1080x24", "-ac"]

# Define environment variable
ENV DISPLAY=:0

# Run your PyQt application
CMD ["python", "diffgui.py"]

