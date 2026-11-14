# NEAR HACKATHON 2026 — final submission checklist

Deadline: **14 November 2026, 23:59 UTC** (15 November, 05:29 IST).

## Completed through GitHub integration (verified 14 Nov)

- [x] Consolidated canonical repository: https://github.com/agentzeta/residual-near
- [x] Preserved Python classifier, formal Lean model, truth table and fixtures
- [x] Integrated browser frontend (`site/`), browser parity tests, demo recorder and summary script
- [x] Committed workflows (`tests.yml`, `pages.yml`, `live-scan.yml`, `demo-video.yml`)
- [x] Published static `gh-pages` branch
- [x] GitHub's **pages build and deployment** workflow succeeded for the static branch
- [x] `residual-near-2026` README links to canonical repository
- [x] Demo recorder now rejects account-check and sample error screens

## Verification still required

- [ ] Open https://agentzeta.github.io/residual-near/ in an incognito browser and confirm the app renders
- [ ] Check a real mainnet account; verify returned block hash, access key list and state
- [ ] Run the browser live sample; verify actual numbers and network completeness warnings
- [ ] Run `python3 -m unittest discover -s tests -v` and `node --test tests/web/parity.test.mjs` locally if GitHub Actions still cannot start a runner
- [ ] Investigate GitHub Actions **Tests** failure: no step logs / no runner was assigned in the initial run; do not claim tests passed in CI
- [ ] Produce and review one mainnet scan report, either locally or via the `Live mainnet scan` workflow if Actions becomes available
- [ ] Produce a real video or screenshots, review them, and publish on X tagged @NEARProtocol #NEARHackathon
- [ ] Set up or confirm your own NEAR account ID (public address only)
- [ ] Submit once at https://nearhackathon.com/ with public repository URL and X demo post URL, before the deadline
- [ ] Save the confirmation, and keep the public repo and site running through judging

**Never** represent fixture data as a live measurement. No contract, wallet signature, NEAR Intents integration or transaction is required. See `docs/DEPLOY.md` for the Actions-free Pages publishing fallback.
