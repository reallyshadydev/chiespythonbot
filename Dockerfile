# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY scripts/requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# Define environment variables (can be overridden at runtime)
# These are placeholders; they should be passed securely during 'docker run'
ENV RPC_HOST="127.0.0.1"
ENV RPC_PORT="18332"
ENV RPC_USER="your_rpc_user"
ENV RPC_PASSWORD="your_rpc_password"
ENV NODE_OPERATOR_ADDRESS="your_btc_address"
ENV NODE_OPERATOR_FEE_PERCENT="0.5"

# Command to run the application
CMD ["python", "scripts/main.py"]
