# Use a Python base image
FROM python:3.9-slim-buster


ENV VAULT_URL=my_value

# Set the working directory to /app
WORKDIR /app



# Copy the operator code into the container
COPY python-operator.py /app

# Install the required packages
RUN pip3 install kopf kubernetes requests jq datetime

# Set the command to run the operator
CMD ["kopf", "run", "--standalone", "--verbose", "python-operator.py"]