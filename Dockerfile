# Use an official Python runtime as the base image
FROM python:3.12-slim-bookworm

# Set the working directory in the container to /app
WORKDIR /inventoryTrack

# Add the current directory contents into the container at /app
ADD . /inventoryTrack

# Install Node.js
RUN apt-get update && apt-get install -y nodejs npm

# Install Tailwind CSS and other dependencies
RUN npm install

# Build your CSS
RUN npm run build

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Run app.py when the container launches
CMD ["python", "main.py"]
