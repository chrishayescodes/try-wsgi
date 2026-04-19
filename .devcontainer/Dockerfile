FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    apache2 \
    tree \
    libapache2-mod-wsgi-py3 \
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

# Enable the persistent WSGI engine
RUN a2enmod wsgi

# Silence FQDN warning
RUN echo "ServerName localhost" >> /etc/apache2/apache2.conf

# Create the private silo directory
RUN mkdir -p /var/www/silos

# Startup command
CMD ["/bin/bash", "-c", "source /etc/apache2/envvars && exec /usr/sbin/apache2 -D FOREGROUND"]