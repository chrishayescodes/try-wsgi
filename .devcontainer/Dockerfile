FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    nginx \
    gunicorn \
    tree \
    python3 \
    python3-jinja2 \
    python3-jwt \
    python3-yaml \
    dos2unix \
    curl \
    wget \
    git \
    && apt-get clean

# INSTALL YQ (Mike Farah version) 
# This detects your architecture (Intel vs Apple Silicon) automatically
RUN wget https://github.com/mikefarah/yq/releases/latest/download/yq_linux_$(dpkg --print-architecture) -O /usr/bin/yq && \
    chmod +x /usr/bin/yq

# Create the private silo directory
RUN mkdir -p /var/www/silos

# Create a secure directory for keys
RUN mkdir -p /etc/jwt-keys && chmod 700 /etc/jwt-keys

# Startup command - the most basic persistent process to keep the container alive.
# Services are managed by postcreate.sh.
CMD ["sleep", "infinity"]