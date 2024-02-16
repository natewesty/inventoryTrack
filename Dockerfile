# Use the latest Python image
FROM python:latest

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y curl

# Copy requirements.txt to the working directory
COPY requirements.txt ./

# Update pip
RUN pip install --upgrade pip

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files to the working directory
COPY . .

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Run main.py when the container launches
CMD ["python", "main.py"]