# Using Caddy with QR Code Project

This directory contains Caddy configurations to solve CORS and HTTPS issues in the QR code project.

## What is Caddy?

Caddy is a powerful, enterprise-ready, open source web server with automatic HTTPS written in Go. It's perfect for serving and proxying applications, providing automatic HTTPS, handling CORS properly, and much more.

## Files in this Directory

- `Caddyfile` - Production configuration for use on a server with the domain qr.phonon.io
- `Caddyfile.dev` - Simplified development configuration for local Windows development
- `run_caddy.ps1` - PowerShell script to easily run Caddy

## Installation Instructions

### 1. Install Caddy

1. Visit https://caddyserver.com/download
2. Download the appropriate version for Windows
3. Extract the caddy.exe file to a location on your computer
4. Add that location to your PATH environment variable

Alternatively, you can install Caddy using Chocolatey:
```powershell
choco install caddy
```

### 2. Run Caddy for Development

To run Caddy with the development configuration:

```powershell
cd caddy
.\run_caddy.ps1
```

This will start Caddy on port 8443. You can then access your application at:
- https://localhost:8443

### 3. Run Caddy for Production

To run Caddy with the production configuration:

```powershell
cd caddy
.\run_caddy.ps1 prod
```

## Updating Your Frontend Environment

For development, update your frontend `.env.development` file:

```
VITE_API_URL=https://localhost:8443/api
```

## How This Solves the Problem

Using Caddy as a reverse proxy in front of your application will:

1. **Solve CORS issues** - All requests are made to the same domain, eliminating CORS problems
2. **Provide HTTPS** - Caddy automatically manages HTTPS certificates
3. **Fix Mixed Content warnings** - All content is served over HTTPS
4. **Simplify development** - No need to modify your application code

## Troubleshooting

- **Certificate warnings in development**: Since we're using a self-signed certificate in development, you may see browser warnings. You can click "Advanced" and "Proceed" to continue.

- **Permission issues**: If you get permission errors, try running PowerShell as Administrator.

- **Port conflicts**: If port 8443 is already in use, modify the Caddyfile.dev file to use a different port.

## Production Deployment

For production deployment:

1. Set up a server with the domain qr.phonon.io pointing to it
2. Install Caddy on the server
3. Copy the production Caddyfile to the server
4. Run Caddy with the production configuration
5. Ensure your firewall allows traffic on ports 80 and 443 