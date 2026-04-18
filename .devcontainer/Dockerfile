FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    apache2 \
    libapache2-mod-wsgi-py3 \
    python3 \
    dos2unix \
    curl \
    git \
    && apt-get clean

# Enable the persistent WSGI engine
RUN a2enmod wsgi

# Silence FQDN warning and copy config
RUN echo "ServerName localhost" >> /etc/apache2/apache2.conf
COPY wsgi-silo.conf /etc/apache2/sites-available/000-default.conf

# Create the private silo directory
RUN mkdir -p /var/www/silos

# Startup command to source env and run in foreground
CMD ["/bin/bash", "-c", "source /etc/apache2/envvars && exec /usr/sbin/apache2 -D FOREGROUND"]