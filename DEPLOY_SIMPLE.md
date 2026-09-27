# Put it online in about 10 minutes

The easiest route is **Render**: free, no credit card, no Docker knowledge
needed. You upload the code to GitHub once, point Render at it, and you get a
public HTTPS address.

Everything Render needs is already in this folder (`Dockerfile`,
`render.yaml`), so there are no settings to fill in.

---

## Step 1 — Put the code on GitHub

1. Make a free account at **github.com** if you do not have one.
2. Click the **+** at the top right → **New repository**.
3. Name it `cow-curve-analytics`. Leave it **Private** if the reports are not
   public. Click **Create repository**.
4. On the next page click **uploading an existing file**.
5. Open the `chart_digitizer` folder on your computer, select **everything
   inside it** (not the folder itself), and drag it into the browser.
6. Wait for the upload bar to finish, then click **Commit changes**.

> Drag the *contents*. If you drag the folder, `Dockerfile` ends up one level
> down and Render will not find it.

---

## Step 2 — Connect Render

1. Go to **render.com** → **Get Started** → sign in with GitHub.
2. Click **New +** → **Web Service**.
3. Choose your `cow-curve-analytics` repository.
4. Render reads `render.yaml` and fills everything in. Check that **Runtime**
   says `Docker`, then click **Create Web Service**.

The first build takes 5–10 minutes because it installs OpenCV and PyMuPDF.
Later deploys are much faster.

---

## Step 3 — Open it

When the log shows **Live**, your address appears at the top:

```
https://cow-curve-analytics.onrender.com
```

Open it and upload a PDF. Try `demo/reports/demo_1_normal.pdf` first —
16 charts should come back at 100 % accuracy.

---

## Two things about the free plan

**It sleeps after 15 minutes of no use.** The next visit takes about 50
seconds to wake up. Not broken, just cold.

**The disk resets on every restart.** Extracted CSVs disappear when it sleeps
or redeploys, so download what you need in the same session. Upgrading to the
$7/month plan removes both limits.

---

## Anyone with the link can use it

There is no login. Anyone who has the URL can upload reports and download
every result on the server.

If that is not acceptable, keep the GitHub repository **private** and share
the link only with people you trust — or add a password, which is covered in
`HOSTING.md`.

---

## Updating it later

Upload the changed files to the same GitHub repository. Render notices the
commit and redeploys on its own, usually within a couple of minutes.

---

## If something goes wrong

**"Dockerfile not found"** — the folder contents were not uploaded at the top
level. In GitHub you should see `Dockerfile`, `app.py` and `pipeline/` listed
directly, not inside another folder.

**Build fails on opencv** — check `requirements-server.txt` is present; it
pins the headless build, which is the one that works on a server.

**Page loads but upload fails** — open `https://your-address/build`. If that
returns a build id, the app is running and the problem is the upload itself;
if it does not, the deploy has not finished.

---

## Other options

| Host | Free? | Notes |
|---|---|---|
| **Render** | yes | Easiest. Sleeps when idle |
| **Railway** | trial credit | Same flow, does not sleep |
| **Fly.io** | small free tier | Needs a command-line tool |
| **Your own VPS** | ~€4/month | Full control, keeps files. See `HOSTING.md` |

Start with Render. Moving later is just pointing a different host at the same
repository.
