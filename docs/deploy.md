# Deploying to Vercel

For the owner. About ten minutes, done once. Everything here happens in your own accounts;
the key never goes into the repository.

One Vercel project serves both halves: the Next.js page as static files from the CDN, and the
agent as one Python function under `/api` (C-03, C-07). `vercel.json` says how — you should not
need to change any build setting.

## Before you start

1. **Groq spend limit.** In the Groq console, set a spend limit on the account whose key the
   app will use. The app counts model calls per visitor in a cookie, but a visitor who clears
   cookies resets that count — the spend limit is the guard that holds.
2. **Groq tier.** On the free tier the app manages roughly 6–8 model-assisted searches a minute
   across *all* visitors (8,000 tokens a minute, measured). Past that, answers fall back to the
   plain wording — still correct. Upgrade the Groq account first if you expect more.
3. **Vercel plan.** The Hobby plan is free for non-commercial personal use, which this proof of
   concept is. It does not bill for overage; a project that exceeds its limits is paused.

## Deploy

1. Go to **vercel.com**, sign in with GitHub, and choose **Add New… → Project**.
2. **Import** `desilva23/Task`.
3. On the configuration screen:
   - **Framework Preset:** Next.js (detected from `vercel.json`)
   - **Root Directory:** leave as `./`
   - **Build and Output Settings:** leave the defaults
   - **Environment Variables:** add one —
     - **Key:** `GROQ_API_KEY`
     - **Value:** your key (`gsk_…`)
     - **Environments:** Production (add Preview too if you want branch previews to use the
       model; without the key they use the plain wording)
4. **Deploy.** The first build takes a few minutes: it builds the page with `npm`, and installs
   the Python function's dependencies from `pyproject.toml` and `uv.lock` on Python 3.12.

Vercel then deploys every push: `main` to production, every other branch to its own preview
URL. Work on a branch, check its preview, and merge when the check passes.

## Check it

1. Open `https://<your-project>.vercel.app/api/store` — you should see JSON listing three floors.
2. Open the site on your phone, search `milk, bread, eggs`, add the available items, and plan
   the route.
3. Turn on **Scan a barcode** and allow the camera. Type `2040634867035` into the digits field
   to check the lookup; the demo store's barcodes are synthetic, so a real product's barcode
   correctly says it is not in this store's catalogue.
4. From your machine, run the browser tests against the live site:

   ```bash
   LOCATOR_URL=https://<your-project>.vercel.app uv run pytest tests/browser
   ```

## Stock alerts to the store manager

The store manager is emailed when a product falls to 5 or fewer on the shelf, and again when it
runs out (FR-26). The emails come from a GitHub Action, through AgentMail.

1. In AgentMail, note the **API key** and the **inbox address** you send from (it looks like
   `store23@agentmail.to` — copy it exactly from the dashboard).
2. On GitHub, open `desilva23/Task` → **Settings → Secrets and variables → Actions → New
   repository secret**, and add three:
   - `AGENTMAIL_API_KEY` — the API key
   - `AGENTMAIL_INBOX_ID` — the inbox address
   - `STORE_MANAGER_EMAIL` — where the alerts go
3. To switch alerts on, open **Actions → stock alerts → Run workflow** (leave "current"
   ticked): the manager gets one email listing everything already low and one listing
   everything out. After that, every push that changes `data/SBY-DEMO-001/stock.csv` emails
   only what newly crossed into low or out.

**To demonstrate it**, open **Actions → stock alerts → Run workflow**, choose mode **sale**
and keep (or change) `Whole Milk=3, Bananas=0`. The job pretends that sale happened in a
temporary copy of the store and sends what a real stock update would: one low-stock email and
one out-of-stock email, within a minute or two. Nothing is committed and the site's stock does
not change, so it can be run as often as needed; a product name shared by several sizes needs
its SKU instead.

To see the emails without sending, run
`uv run python -m notify.run --store data/SBY-DEMO-001 --current --dry-run`.

## Optional hardening

- **Rate limit.** In the project's **Firewall**, add a rule that rate-limits `/api/*` per IP
  address, if your plan offers it. It protects the Groq key better than the cookie does.
- **Deployment Protection.** Previews are protected by Vercel authentication by default; leave
  that on so only you can use branch previews.

## Retiring the Streamlit app

The Streamlit Community Cloud app follows `main`, and `main` no longer has a Streamlit page once
this change is merged — its next redeploy fails. After the Vercel site works, delete it: open
**share.streamlit.io**, find the app, **⋮ → Delete**. Do not delete the old branch
`claude/planogram-store-navigation-czn7bh` while any app still deploys from it.

## If something goes wrong

- **The page loads but every search apologises.** Open the project's **Logs** in Vercel and
  look at the `/api/index` function. A missing data folder or an import error shows there.
- **Answers always say "Plain wording".** The key is missing from the environment the
  deployment ran in, or the Groq budget is spent. Add the variable and **Redeploy**.
- **The camera never starts.** The browser refused it — the site must be on `https://` (C-08),
  and the shopper must allow the camera. The typed digits work either way.
