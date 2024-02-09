# Use an official Python runtime as the base image
FROM python:3.9-slim-buster

# Set the working directory in the container to /app
WORKDIR /app

# Add the current directory contents into the container at /app
ADD . /app

# Install system dependencies
RUN apt-get update && apt-get install -y curl

# Install Node.js
RUN curl -sL https://deb.nodesource.com/setup_lts.x | bash -
RUN apt-get install -y nodejs

# Install Tailwind CSS, PostCSS, and other dependencies
RUN npm install
RUN npm install -g postcss postcss-cli tailwindcss autoprefixer

# Create a basic PostCSS config file
RUN echo "module.exports = { plugins: [require('tailwindcss'), require('autoprefixer')]};" > src/postcss.config.js

# Create a basic Tailwind CSS file
RUN echo "@import 'tailwindcss/base'; @import 'tailwindcss/components'; @import 'tailwindcss/utilities';" > src/style.css

# Build your CSS
RUN npx postcss src/style.css -o static/output.css

# Update pip
RUN pip install --upgrade pip

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Run main.py when the container launches
CMD ["python", "main.py"]