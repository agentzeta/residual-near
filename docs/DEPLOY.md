# Deploying the live demo

Nothing is deployed on NEAR itself: Residual only reads the chain. The demo is a static site on GitHub Pages that reads NEAR mainnet from the visitor's browser, plus a daily snapshot made by GitHub Actions.

1. Make sure these files are in the repository, including the hidden `.github` folder: `site/`, `scripts/summary.py`, `demo/record.cjs`, `tests/web/parity.test.mjs`, `.github/workflows/pages.yml`, `.github/workflows/demo-video.yml`, `.github/workflows/tests.yml`, `.github/workflows/live-scan.yml`.
2. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
3. **Actions** tab: if asked, enable workflows. Open **Deploy site** and press **Run workflow** (it also runs by itself on every push to `main`).
4. When it finishes (about 3–6 minutes, most of it the 200-account mainnet scan), the run page shows the snapshot table and the site URL: `https://agentzeta.github.io/residual-near/`.
5. Open the site. Under **Check an account**, press the `near` chip: you should see a state, a block height and the account's keys within a few seconds. Then press **Run now** under **Live sample**.

If the browser shows "No NEAR RPC endpoint answered", the public endpoints are rate-limiting or blocking your network; try again or switch network. If the daily snapshot shows many `RPC_ERROR` accounts, add a free FastNear API key as the repository secret `FASTNEAR_API_KEY` (Settings → Secrets and variables → Actions) and rerun **Deploy site**. The key is used only inside GitHub Actions and never reaches the site.

## Recording the demo video

**Actions → Record demo video → Run workflow.** It takes a fresh mainnet snapshot, opens the site in a headless browser, checks a real account, runs a live sample against mainnet, and uploads **residual-demo-video**: `residual-demo.mp4` (1280×720, H.264, about 1.5–2 minutes, ready for X) and seven PNG screenshots of each step. Download it from the bottom of the run page.

To record on your own machine instead: `python3 -m http.server 8000 --directory site &` then `npm install playwright@1.49.1 && npx playwright install chromium && node demo/record.cjs http://127.0.0.1:8000/`.

Keep the site up through judging (16–18 November) and ideally until 25 November.
