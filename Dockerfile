# Base image
FROM python:3.9-slim

# Set working directory inside the container
WORKDIR /app

# Copy the script into the container
COPY . /app

# Install necessary packages
RUN pip install requests cereal

# Set environment variables (you can override them in docker-compose.yml)
ENV DB_PATH=/app/gps_data.db
ENV BUFFER_SIZE=10
ENV SERVER_URL=https://osmand.nzmdn.me/

# Run the script
CMD ["python", "gps_tracker.py"]
