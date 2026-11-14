# Running the live mainnet scan

Two ways: on GitHub with one click (no local setup), or on your own machine.

## Option A: GitHub Actions (no local setup)

1. On the repository page, open **Actions**, choose **Live mainnet scan**, then **Run workflow** (keep 200 and 60).
2. Wait for the run to finish (a few minutes). The run page shows a **Residual mainnet sample** table: chain, protocol version, block height and hash, counts, warnings.
3. Under **Artifacts**, download **residual-mainnet-report** and unzip it. It holds `report.json`, `observations.json` and `index.html`.
4. Commit those three files to `evidence/mainnet-YYYYMMDD/` (on github.com: **Add file → Upload files**, and type `evidence/mainnet-YYYYMMDD/` in front of the names, or drag the folder in).
5. Check and report the result as in steps 3 and 5 below.

If the run shows many `RPC_ERROR` accounts or a "Sampling frame incomplete" warning, add a free FastNear key as a repository secret named `FASTNEAR_API_KEY` (**Settings → Secrets and variables → Actions**) and run it again.

## Option B: your own machine

Needs Python 3.9+ and an internet connection. Nothing to install.

### 1. Check the build

```bash
python3 -m unittest discover -s tests -v
```

All 40 tests should pass.

### 2. Run the reproducible sample

```bash
python3 -m residual --sample-signers 200 --window-blocks 60 --output evidence/mainnet-$(date -u +%Y%m%d)
```

Expect roughly 600 to 1,000 RPC calls (one block and a few chunks per block in the window, then one read per account). On FastNear's public endpoint this takes a few minutes. If you are rate-limited (many `RPC_ERROR` accounts, or a "Sampling frame incomplete" warning), get a free key from FastNear and rerun with:

```bash
export FASTNEAR_API_KEY=your-key
```

The key is sent as a Bearer header and never written to any file.

### 3. Check the result before you claim anything

Open `evidence/mainnet-YYYYMMDD/index.html` (or serve the folder with `python3 -m http.server`). Confirm:

- **Chain** reads `mainnet` and **Protocol version** is 85 or higher.
- There are **no warnings** at the top. If there are, say so in the submission or rerun.
- **Unresolved** is small, and its reasons make sense.
- Note the **block height and hash**, the **window** and the **frame size** (distinct signers).

### 4. Commit the evidence

```bash
git add evidence/
git commit -m "Mainnet sample at block <height>"
git push
```

Commit the whole folder: `report.json`, `observations.json` and `index.html`. Anyone can then check the digests and rerun the sample from the recorded block.

### 5. Report it honestly

Write the result as: "At NEAR mainnet block <height> (<hash>), a seeded random draw of <n> from <frame> distinct transaction signers in blocks <a>–<b> found <x> accounts with a PQ key present, <y> still holding a classical full-access key, and <z> PQ-only." Add the enrollers cohort if one appears ("<k> accounts enrolled an ML-DSA-65 key in the window; <j> of them still hold a classical full-access key").

Do not describe it as all of NEAR. The frame is recently active signers, which over-represents bots and relayers. A result of zero PQ adopters in the sample is a valid, reportable finding: adoption is new.

## Optional: hand-picked accounts

To check accounts you know have added ML-DSA keys (for example, your own testnet or mainnet test account):

```bash
printf 'your-account.near\n' > my-accounts.txt
python3 -m residual --accounts my-accounts.txt --output evidence/handpicked
```

Report it as a convenience sample, never as a population figure.
