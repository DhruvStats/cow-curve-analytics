# Hosting Chart Digitizer online

The app is a small Flask service. It needs no database and no external
services, so hosting is mostly a matter of running one container.

## Before you deploy: three things that matter

**1. Jobs live in memory.** The job registry is a Python dict inside the
process. Restart the server and in-flight jobs are lost, and **two worker
processes cannot see each other's jobs**. That is why the supplied
configuration runs a single worker with several threads. Do not raise
`--workers` above 1 without moving the registry to Redis first.

**2. Nothing is deleted automatically.** Every upload leaves a PDF in
`uploads/` and a folder of CSVs in `output/`. On a host with a small disk this
will eventually fill it. Either add a cron job to clear files older than a day,
or use a host that resets the filesystem on each deploy and accept that old
results disappear then.

**3. There is no login.** Anyone with the URL can upload a PDF and download
every result on the server, including other people's. If the reports are not
public, put the service behind authentication — see *Adding a password* below.

---

## Option A — Docker on any VPS (recommended)

Works on Hetzner, DigitalOcean, AWS Lightsail, a university server, anything
that runs Docker. You keep the disk, so results persist.

```bash
docker build -t chart-digitizer .
docker run -d --name chart-digitizer \
  -p 80:8080 \
  -v chartdata:/app/output \
  --restart unless-stopped \
  chart-digitizer
```

Open `http://your-server-ip`.

The `-v chartdata:/app/output` keeps extracted CSVs across container restarts.
Drop it if you would rather results vanish on redeploy.

### Keeping the disk from filling

```bash
# once a day, delete job folders older than 24h
0 3 * * * docker exec chart-digitizer find /app/output -mindepth 1 -maxdepth 1 -type d -mtime +1 -exec rm -rf {} +
0 3 * * * docker exec chart-digitizer find /app/uploads -type f -mtime +1 -delete
```

---

## Option B — Render / Railway / Fly.io

These build the Dockerfile for you and give you an HTTPS URL. Push the folder
to a Git repository, point the service at it, and they do the rest. `Procfile`
and `Dockerfile` are both included, so either build style works.

Set nothing special; the image already reads `$PORT`.

**Watch the free tiers.** They usually sleep after inactivity and wipe the
filesystem on restart, so a job finished before the sleep will have lost its
CSVs. Fine for demonstrating, not for daily work.

---

## Option C — Behind your existing web server

If you already run nginx or Apache, run the container on localhost and proxy
to it. This is also the easiest place to add HTTPS and a password.

```nginx
server {
    server_name curves.example.com;

    # Reports can be large and extraction takes a while.
    client_max_body_size 64M;
    proxy_read_timeout 300s;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Then `certbot --nginx -d curves.example.com` for a certificate.

---

## Adding a password

The quickest safe option is HTTP basic auth at the proxy, which needs no code
change:

```bash
sudo apt install apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd yourname
```

```nginx
location / {
    auth_basic "Chart Digitizer";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://127.0.0.1:8080;
    # ...the proxy headers from above
}
```

---

## Sizing

| Resource | Needed | Why |
|---|---|---|
| RAM | 1 GB | PyMuPDF rasterises a page at a time |
| CPU | 1 core | Extraction is a few seconds per report |
| Disk | 2 GB + results | The image is ~600 MB; each report's output is ~1 MB |

A €4/month VPS handles this comfortably.

---

## Checking a deployment

```bash
curl https://your-url/build
```

Should return the build id and CSV column list. If that works, the app is up
and serving the right code.

Then upload `demo/reports/demo_1_normal.pdf` through the browser: 16 charts
should come back, all at 100 % milk accuracy.
