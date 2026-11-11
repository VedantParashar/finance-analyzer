# Deploying to Streamlit Community Cloud

[Streamlit Community Cloud](https://streamlit.io/cloud) hosts Streamlit apps for free, straight from a
GitHub repository. The repo is already prepared; the steps below need your accounts, so only you can do them.

**Not tested for real:** the app was run locally through the cloud entry point (`streamlit_app.py`), but
an actual deployment needs your login. If a step fails, see "If something goes wrong" below.

## What's already in the repo

| File | Why |
|---|---|
| `streamlit_app.py` | The file Community Cloud runs. It starts the same app as `uv run finance-analyzer`. |
| `uv.lock` | The dependency file. Community Cloud looks for `uv.lock` first and installs exactly those versions. No `requirements.txt` is needed, and adding one would be ignored. |
| `.streamlit/config.toml` | Streamlit settings, read from the repo root. |
| `app.py` reads `SEC_USER_AGENT` from Streamlit secrets | Hosted apps have no `.env` file; secrets replace it. Locally, `.env` still works. |

## Steps

1. **Merge the pull requests into `master`** and check the tests are green on GitHub.
2. Go to **https://share.streamlit.io** and sign in with your GitHub account. Allow it to see the
   `finance-analyzer` repository when asked.
3. Click **Create app** (top right). When asked "Do you already have an app?", choose
   **Yup, I have an app**.
4. Fill in:
   - **Repository:** `VedantParashar/finance-analyzer`
   - **Branch:** `master`
   - **Main file path:** `streamlit_app.py`
   - **App URL** (optional): pick a short name, e.g. `finance-analyzer`
5. Click **Advanced settings**:
   - **Python version:** `3.12`
   - **Secrets:** paste this one line, with your own name and email (the SEC asks every client to say
     who it is; it is the same value as in your `.env`):
     ```toml
     SEC_USER_AGENT = "Finance Analyzer you@example.com"
     ```
   - Click **Save**.
6. Click **Deploy** and wait for the log on the right to finish (a few minutes the first time).
7. **Check it works:** type `AAPL` on the Company page. You should see Apple's line items, the metric
   cards, the valuation section and the data checks. Then try `AAPL, KO, NVDA` on the Compare page.
8. Put the app's URL at the top of `README.md` so visitors can try it.

To change the secret later: open your app list at share.streamlit.io, click the **⋮** next to the app,
then **Settings → Secrets**.

## Things that behave differently when hosted

- **Stored data is temporary.** The SEC downloads and the DuckDB file live on the app's own disk, which
  is wiped when the app restarts or goes to sleep. Nothing is lost: a company is simply downloaded again
  the next time someone looks at it (a few seconds).
- **Share prices may be unavailable.** Yahoo Finance often blocks requests from cloud servers. The five
  valuation metrics then read "unavailable" and everything else still works.
- **Anyone with the URL can use it**, and every SEC request is made under your `SEC_USER_AGENT`. The SEC
  allows up to 10 requests per second; this app makes at most three per company.
- **Usage statistics are switched on.** Community Cloud overrides the `gatherUsageStats = false` setting
  in `.streamlit/config.toml`.
- **Updates are automatic.** Every push to `master` redeploys the app.

## If something goes wrong

- **"Set SEC_USER_AGENT…" appears in the app:** the secret is missing or misspelt. Fix it under
  Settings → Secrets; the name must be exactly `SEC_USER_AGENT`, with the value in double quotes.
- **The install step fails in the log:** Community Cloud is trying to install from `uv.lock`. As a
  fallback, create a pip-style file, commit it and reboot the app:
  ```bash
  uv export --no-dev --no-emit-project --no-hashes -o requirements.txt
  git rm --cached uv.lock   # Community Cloud uses only one dependency file, and uv.lock wins
  ```
  That stops tracking `uv.lock` in git, which the tests on GitHub and the Dockerfile need, so only do
  this on a separate deployment branch and point the app's **Branch** at it.
- **`ModuleNotFoundError: finance_analyzer`:** the Main file path is wrong. It must be
  `streamlit_app.py`, not `src/finance_analyzer/app.py`.
