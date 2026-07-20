FROM python:3.14

RUN pip install --root-user-action=ignore --upgrade pip

# Set the working directory to /app
WORKDIR /app
# I prefer not to COPY the entire project into the container, as it may contain sensitive information or unnecessary files.
# Instead, I mount the application directory from the host through a volume.

# Copy requirements for the authentication service
COPY ./authentication_requirements.txt /app/authentication_requirements.txt

# Install dependencies required for the authentication service
RUN pip install --no-cache-dir --root-user-action=ignore --upgrade -r /app/authentication_requirements.txt