# Raspberry Pi Deployment & Mobile Distribution Guide

This guide walks through hosting the Sunsynk dashboard stack on a Raspberry Pi that lives on your home network while exposing the HTTPS API on `zuva.robasta.com` (or any other subdomain) and distributing the Android client privately (APK sideload). It focuses on:

- Preparing a reliable Raspberry Pi host with Docker
- Publishing the FastAPI backend and WebSocket notifications securely via Nginx + TLS
- Enabling notification channels (WebSocket push + Twilio)
- Building and installing the Android app outside the Play Store while pointing it to your domain

> **Topology overview**: Raspberry Pi (Docker) → InfluxDB + data collector + FastAPI backend + React web dashboard behind Nginx. Router forwards 80/443 to the Pi so the world reaches `zuva.robasta.com`. Android app talks to `https://zuva.robasta.com/api` and keeps a WebSocket open to receive alerts.

## 1. Hardware & Network Prerequisites
- Raspberry Pi 4 Model B (4 GB RAM minimum, 8 GB recommended) + high-endurance SSD or NVMe HAT (avoid SD wear).
- 64-bit Raspberry Pi OS Lite (Debian Bookworm) on the SSD.
- Stable Ethernet connection (preferred) with DHCP reservation or static IP on your router.
- Home router that supports port forwarding for TCP 80 and 443. If your ISP blocks inbound 80/443, plan for Cloudflare Tunnel or Tailscale Serve instead.
- robasta.com DNS management access to add the `zuva` subdomain.

## 2. Base OS Preparation
1. Boot the Pi, log in via SSH, and update the system:
   ```bash
   sudo apt update && sudo apt full-upgrade -y
   sudo reboot
   ```
2. Set hostname/timezone and enable SSH if not already done:
   ```bash
   sudo raspi-config nonint do_hostname zuva-pi
   sudo raspi-config nonint do_change_timezone Africa/Johannesburg
   sudo systemctl enable ssh --now
   ```
3. Lock down the default user (create a new admin, disable password SSH, add your keys) and optionally enable `ufw` with only 22/80/443 open.
4. Reserve the Pi’s MAC in your router or configure a static IP (e.g., `192.168.1.50`).

## 3. Install Docker Engine & Compose Plugin
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
sudo systemctl enable docker --now
sudo apt install -y docker-compose-plugin
```
Verify:
```bash
docker version
docker compose version
```

## 4. Clone the Repository & Configure Environment
```bash
cd /opt
sudo git clone https://github.com/robasta/zuva.git sunsynk-api-client-main
sudo chown -R $USER:$USER sunsynk-api-client-main
cd sunsynk-api-client-main/sunsynk-dashboard
cp .env.template .env
```
Edit `.env` with real secrets. At minimum set:
- `SUNSYNK_USERNAME` / `SUNSYNK_PASSWORD`
- `OPENWEATHER_API_KEY` and `LOCATION`
- Influx admin password/token if you don’t want the defaults
- `JWT_SECRET_KEY` (random 32+ chars)
- `CORS_ORIGINS=https://zuva.robasta.com` (add other origins as needed)
- `REACT_APP_API_URL=https://zuva.robasta.com/api`
- `REACT_APP_WS_URL=wss://zuva.robasta.com/ws/dashboard`
- Notification keys (Twilio, FCM) so that alerts can reach both SMS/WhatsApp and mobile WebSocket clients.
- `ALERT_COOLDOWN_MINUTES` (default 20) to set the global "no repeat" window plus optional `ALERT_COOLDOWN_OVERRIDES` JSON for per-category timing (e.g. `{ "battery_low": "45min" }`).

Create directories that persist outside containers:
```bash
mkdir -p logs backups nginx/ssl
```

## 5. Launch the Core Stack on the Pi
Start the core services (database, collectors, backend, frontend). Include the production Nginx proxy so TLS termination works later:
```bash
cd ~/sunsynk-api-client-main/sunsynk-dashboard
docker compose --profile production up -d influxdb data-collector dashboard-api web-dashboard nginx
```
(Optional) Add monitoring extras when ready:
```bash
docker compose --profile monitoring up -d grafana prometheus node-exporter loki promtail
```
Check status:
```bash
docker compose ps
docker compose logs -f dashboard-api
```

## 6. DNS, Port Forwarding, and TLS Certificates
1. **DNS** – Create an `A` record in your robasta.com DNS panel:
   - Name: `zuva`
   - Type: `A`
   - Value: your home WAN IP (update when IP changes or use a dynamic DNS provider).
2. **Port forwarding** – Forward TCP 80 and 443 from the router to the Pi’s IP. If CGNAT blocks inbound ports, use Cloudflare Tunnel or Tailscale Serve as an alternative.
3. **TLS via Let’s Encrypt** – Stop Nginx temporarily, request a cert, then copy it into the repo-managed volume:
   ```bash
   cd ~/sunsynk-api-client-main/sunsynk-dashboard
   docker compose stop nginx
   sudo apt install -y certbot
   sudo certbot certonly --standalone -d zuva.robasta.com --agree-tos -m you@robasta.com --non-interactive
   sudo cp /etc/letsencrypt/live/zuva.robasta.com/fullchain.pem nginx/ssl/fullchain.pem
   sudo cp /etc/letsencrypt/live/zuva.robasta.com/privkey.pem nginx/ssl/privkey.pem
   sudo chown $USER:$USER nginx/ssl/*.pem && chmod 600 nginx/ssl/privkey.pem
   docker compose start nginx
   ```
4. **Nginx config** – Update `sunsynk-dashboard/nginx/nginx.conf` to set the server name and enable HTTPS:
   ```nginx
   server {
       listen 80;
       server_name zuva.robasta.com;
       return 301 https://$host$request_uri;
   }

   server {
       listen 443 ssl;
       server_name zuva.robasta.com;
       ssl_certificate /etc/nginx/ssl/fullchain.pem;
       ssl_certificate_key /etc/nginx/ssl/privkey.pem;
       # existing proxy_pass blocks remain
   }
   ```
   Reload the container after editing:
   ```bash
docker compose restart nginx
   ```
5. Automate renewals with a cron entry that renews monthly and restarts Nginx if certificates change.

## 7. Security & Reliability Hardening
- Enable `ufw`/`nftables` and rate-limit SSH, keep the Pi patched (`sudo unattended-upgrades`).
- Consider Tailscale or WireGuard to access the Pi privately, even if the dashboard is public.
- Turn on the Watchtower service to auto-update containers (`docker compose --profile production up -d watchtower`).
- Use the built-in backup container or schedule `influx backup` jobs to a NAS/Cloud bucket.
- Monitor with Grafana/Prometheus (enable the monitoring profile) and set alerts for resource usage.

## 8. Notification Services Configuration
1. **Twilio / SMS / WhatsApp / Voice** – Populate the Twilio credentials in `.env`. Use the `WHATSAPP_FROM`, `SMS_TO`, and `VOICE_TO` placeholders with verified numbers.
2. **Push via WebSocket** – The mobile client receives alerts through `/ws/dashboard`. Ensure `REACT_APP_WS_URL` and the mobile config both reference `wss://zuva.robasta.com/ws/dashboard`.
3. **Firebase Cloud Messaging** (optional) – Set `FCM_API_KEY` if/when the backend gains push token storage.
4. **Testing** – After logging into the dashboard (or using `http://localhost:8000/docs`), trigger a test alert:
   ```bash
   curl -X POST https://zuva.robasta.com/api/alerts/test \
     -H "Authorization: Bearer <jwt>" \
     -H "Content-Type: application/json" \
     -d '{"severity": "high"}'
   ```
   Confirm it appears in the web UI and on the Android notification shade.

## 9. Android App Configuration & Sideloading
### 9.1 Point the app at your domain
Edit `mobile/shared/src/commonMain/kotlin/com/sunsynk/mobile/shared/network/SunsynkApiConfig.kt` so the defaults are your public endpoints:
```kotlin
data class SunsynkApiConfig(
    val baseUrl: String = "https://zuva.robasta.com/api",
    val websocketUrl: String = "wss://zuva.robasta.com/ws/dashboard",
    ...
)
```
Alternatively, provide an override via a Koin module in `androidApp/src/main/java/com/sunsynk/mobile/di/AndroidModules.kt` if you want to keep localhost defaults for dev builds.

### 9.2 Build a signed release APK
1. Create (or reuse) a release keystore:
   ```bash
   keytool -genkeypair -v -keystore ~/keystores/zuva-release.keystore \
     -alias zuvaRelease -keyalg RSA -keysize 4096 -validity 3650
   ```
2. Add the signing config to `mobile/gradle.properties` (never commit real secrets):
   ```
   ZUVA_KEYSTORE=../keystores/zuva-release.keystore
   ZUVA_KEY_ALIAS=zuvaRelease
   ZUVA_KEY_PASSWORD=<pass>
   ZUVA_STORE_PASSWORD=<pass>
   ```
   Wire these vars inside `mobile/androidApp/build.gradle.kts` signingConfig if not already present.
3. Build the release artifact:
   ```bash
   cd ~/sunsynk-api-client-main/mobile
   ./gradlew clean androidApp:assembleRelease
   ```
   The APK lives at `mobile/androidApp/build/outputs/apk/release/androidApp-release.apk`.

### 9.3 Install on your phone (no Play Store)
1. Enable **Developer options → USB debugging** and **Install unknown apps** on the device.
2. Connect via USB and trust the PC, then sideload:
   ```bash
   adb devices
   adb install -r androidApp/build/outputs/apk/release/androidApp-release.apk
   ```
   (Alternatively, share the APK via secure download link and install directly on-device.)
3. On first launch the app requests notification permission; accept it so `SystemAlertNotifier` can surface WebSocket alerts.

### 9.4 Validate notifications
1. Log in with your Sunsynk credentials.
2. Leave the app in the background—`AlertStreamController` keeps the WebSocket alive and hands alerts to `NotificationCompat` channels.
3. Trigger `/api/alerts/test` and confirm the Android notification appears with the right severity channel (`alerts_high`, etc.).
4. Acknowledge/resolve inside the app and verify the backend reflects the change.

## 10. Maintenance Checklist
- Run `docker compose pull && docker compose up -d` monthly to pick up base image security updates.
- Check disk usage (`docker system df`, `df -h`) so InfluxDB does not fill the SSD.
- Renew TLS certs via `certbot renew` cron and reload Nginx.
- Back up `backups/`, `.env`, and Influx data (`docker compose exec influxdb influx backup /backup`).
- Periodically re-run the mobile build after backend changes that adjust API contracts.

Following the above steps yields a Pi-hosted Sunsynk stack reachable at `https://zuva.robasta.com` with working notifications and a privately distributed Android companion app.```}