#!/usr/bin/env bash
set -e

echo "📦 Installing Oracle Instant Client..."

# Create directory
mkdir -p /opt/oracle
cd /opt/oracle

# Download Instant Client (Basic Lite - small & fast)
curl -L -o instantclient.zip \
https://download.oracle.com/otn_software/linux/instantclient/219000/instantclient-basiclite-linux.x64-21.9.0.0.0dbru.zip

# Unzip
unzip instantclient.zip
rm instantclient.zip

# Enter client directory
cd instantclient_21_9

# Create required symlinks
ln -s libclntsh.so.* libclntsh.so
ln -s libocci.so.* libocci.so

echo "✅ Oracle Instant Client installed at /opt/oracle/instantclient_21_9"
