# Caddy Reverse Proxy Configuration

This document explains how the Caddy reverse proxy is configured in the QR Code Tracking System.

## Overview

Caddy is used as a reverse proxy to:

1. Provide HTTPS termination with automatic TLS certificate management
2. Route requests to the appropriate backend services
3. Handle domain-based routing for qr.phonon.io
4. Serve as the public-facing entry point for the application

## Configuration File

The Caddy configuration is defined in `microservices/caddy/Caddyfile`. Here's an explanation of the key components:

```
{
	# Global options
	debug

	log {
		output file /data/access.log {
			roll_size 10MB
			roll_keep 10
			roll_keep_for 168h
		}
		format json
		level INFO
	}
}

qr.phonon.io {
	# Use the provided certificate and key
	tls /etc/caddy/certs/qr.phonon.io.crt /etc/caddy/certs/qr.phonon.io.key

	# Enable HTTP compression
	encode gzip zstd

	# Handle ACME challenge requests for Let's Encrypt SSL
	handle /.well-known/acme-challenge/* {
		respond "OK" 200
	}

	# Handle requests starting with /api/
	handle_path /api/* {
		# Proxy to the API gateway using plain HTTP within the Docker network
		reverse_proxy http://api-gateway:8000 {
			trusted_proxies private_ranges

			header_up Host {host}
			header_up X-Real-IP {remote_host}
		}
	}

	# Logging for this specific site
	log {
		output file /data/qr.phonon.io.log {
			roll_size 10MB
			roll_keep 10
			roll_keep_for 168h
		}
		format json
		level DEBUG
	}
}
```

## Key Components Explained

### Global Options

```
{
	debug
	log {
		output file /data/access.log {
			roll_size 10MB
			roll_keep 10
			roll_keep_for 168h
		}
		format json
		level INFO
	}
}
```

- `debug`: Enables debug mode for more verbose logging
- `log`: Configures global logging
  - `output file`: Logs are written to a file
  - `roll_size`: Log files are rotated when they reach 10MB
  - `roll_keep`: Keep the last 10 log files
  - `roll_keep_for`: Keep log files for 168 hours (7 days)
  - `format json`: Logs are in JSON format for easier parsing
  - `level INFO`: Log level is set to INFO

### Site Configuration

```
qr.phonon.io {
	# TLS configuration
	tls /etc/caddy/certs/qr.phonon.io.crt /etc/caddy/certs/qr.phonon.io.key

	# Compression
	encode gzip zstd

	# ...
}
```

- `qr.phonon.io`: This block applies to requests for the qr.phonon.io domain
- `tls`: Specifies the TLS certificate and key files
- `encode`: Enables compression for responses using gzip and zstd algorithms

### API Routing

```
handle_path /api/* {
	reverse_proxy http://api-gateway:8000 {
		trusted_proxies private_ranges

		header_up Host {host}
		header_up X-Real-IP {remote_host}
	}
}
```

- `handle_path /api/*`: Matches requests with paths starting with /api/
- `reverse_proxy`: Forwards requests to the API Gateway service
- `trusted_proxies`: Specifies which IP ranges are trusted proxies
- `header_up`: Sets headers on the upstream request
  - `Host`: Preserves the original host header
  - `X-Real-IP`: Sets the client's real IP address

### Site-Specific Logging

```
log {
	output file /data/qr.phonon.io.log {
		roll_size 10MB
		roll_keep 10
		roll_keep_for 168h
	}
	format json
	level DEBUG
}
```

- Site-specific logging configuration
- More detailed logging (DEBUG level) for this specific site

## Docker Configuration

Caddy is deployed as a Docker container with the following configuration in `docker-compose.yml`:

```yaml
caddy:
  image: caddy:latest
  container_name: qr-caddy
  restart: always
  ports:
    - "80:80"    # Needed for HTTP->HTTPS redirects and ACME HTTP challenge
    - "443:443"  # Standard HTTPS port
    - "443:443/udp" # Needed for HTTP/3
  volumes:
    # Mount the Caddyfile
    - ./caddy/Caddyfile:/etc/caddy/Caddyfile
    # Mount the TLS certificates
    - ./caddy/certs:/etc/caddy/certs:ro
    - caddy_data:/data                 # Persists certificates and other Caddy state
    - ./caddy/logs:/data/logs          # Store logs
  networks:
    - qr-network
  environment:
    - CADDY_ADAPTER=caddyfile  # Explicitly set the adapter
    - XDG_DATA_HOME=/data      # Set data directory
    - XDG_CONFIG_HOME=/config  # Set config directory
  depends_on:
    - api-gateway # Ensure API gateway is started before Caddy tries proxying
  command: ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
```

Key aspects:
- Ports 80 and 443 are exposed for HTTP and HTTPS traffic
- The Caddyfile is mounted from the host
- TLS certificates are mounted from the host
- Caddy data is persisted in a Docker volume
- Logs are stored in a mounted directory
- Caddy is configured to use the Caddyfile adapter
- Caddy depends on the API gateway service

## Benefits of Using Caddy

1. **Automatic HTTPS**: Caddy can automatically obtain and renew TLS certificates from Let's Encrypt
2. **Simple Configuration**: Caddyfile syntax is straightforward and easy to understand
3. **HTTP/3 Support**: Caddy supports the latest HTTP protocols
4. **High Performance**: Caddy is written in Go and designed for high performance
5. **Security**: Caddy follows security best practices by default

## Common Tasks

### Reloading Caddy Configuration

If you make changes to the Caddyfile, you can reload Caddy without restarting the container:

```bash
docker-compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```

### Viewing Caddy Logs

```bash
# View Caddy logs
docker-compose logs caddy

# Follow Caddy logs
docker-compose logs -f caddy
```

### Checking Caddy Status

```bash
docker-compose exec caddy caddy status
```

### Testing Caddy Configuration

```bash
docker-compose exec caddy caddy validate --config /etc/caddy/Caddyfile
```

## Troubleshooting

### Certificate Issues

If you're having issues with TLS certificates:

1. Check that the certificate files exist and are readable:
   ```bash
   docker-compose exec caddy ls -la /etc/caddy/certs
   ```

2. Verify the certificate is valid:
   ```bash
   docker-compose exec caddy openssl x509 -in /etc/caddy/certs/qr.phonon.io.crt -text -noout
   ```

### Proxy Issues

If requests aren't being properly proxied to backend services:

1. Check that the backend service is running:
   ```bash
   docker-compose ps api-gateway
   ```

2. Verify network connectivity between Caddy and the backend service:
   ```bash
   docker-compose exec caddy ping api-gateway
   ```

3. Check Caddy logs for proxy errors:
   ```bash
   docker-compose exec caddy cat /data/qr.phonon.io.log | grep "proxy"
   ```

### Performance Issues

If you're experiencing performance issues:

1. Check Caddy resource usage:
   ```bash
   docker stats qr-caddy
   ```

2. Monitor request latency in the logs:
   ```bash
   docker-compose exec caddy cat /data/qr.phonon.io.log | grep "latency"
   ```

## References

- [Caddy Documentation](https://caddyserver.com/docs/)
- [Caddyfile Directives](https://caddyserver.com/docs/caddyfile/directives)
- [Caddy Docker Image](https://hub.docker.com/_/caddy)
