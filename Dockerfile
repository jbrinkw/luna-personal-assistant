# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
# Ensure all necessary modules (api.py, app.py, db/, helpers/, routers/, etc.) are copied
COPY . .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable (optional, can be set during run)
# ENV NAME World

# Run api.py when the container launches using uvicorn
# Use 0.0.0.0 to make it accessible externally
# Remove reload=True for production
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"] 