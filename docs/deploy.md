# Deploying to Streamlit Community Cloud

For the owner. About ten minutes, done once. Everything here happens in your own accounts;
the key never goes into the repository.

## Before you start

1. **Groq spend limit.** In the Groq console, set a spend limit on the account whose key the
   app will use. The app caps model calls per visitor, but a public URL can have many visitors.
2. **Groq tier.** On the free tier the app manages roughly 6–8 model-assisted searches a minute
   across *all* visitors (8,000 tokens a minute, measured). Past that, answers fall back to the
   plain wording — still correct. Upgrade the Groq account first if you expect more.

## Deploy

1. Go to **share.streamlit.io** and sign in with the GitHub account that owns
   `desilva23/Task`.
2. **Create app** → **Deploy a public app from GitHub**.
3. Fill in:
   - **Repository:** `desilva23/Task`
   - **Branch:** `claude/planogram-store-navigation-czn7bh` (or `main`, once merged)
   - **Main file path:** `app.py`
   - **App URL:** your choice
4. Open **Advanced settings**:
   - **Python version:** `3.12` (the default — keep it; the project is pinned to 3.12)
   - **Secrets:** paste exactly one line, with your key between the quotes:
     ```toml
     GROQ_API_KEY = "gsk_your_key_here"
     ```
5. **Deploy.** The first build takes a few minutes; it installs from `uv.lock`.

## Check it

- Search **Coca-Cola Classic**: you should see "In stock", floor 1, aisle 7, rack 3, shelf 2, a
  route, and friendly wording. If you see *"Plain wording: the language model wasn't used"*, the
  key is missing or wrong — fix it under the app's **Settings → Secrets**.
- Send Claude the app URL: it runs the 390 px phone test against the live site.

## Options, no code change

Top-level secrets also become environment variables, so these can go in the Secrets field too:

| Line | Effect |
|---|---|
| `LOCATOR_STORE = "data/SBY-PORT-002"` | Serve the two-floor portability store instead of the demo store |
| `LOCATOR_MODEL = "off"` | Run on the deterministic wording only — no Groq calls at all |

## If something goes wrong

The page never shows a stack trace (by design). Use **Manage app** (bottom right of the live
app) → **Logs** to see the error, and share the log lines with Claude — after checking they
contain no key.
