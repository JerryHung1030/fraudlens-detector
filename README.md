# ScamShield‑AI

**Real‑time scam‑post detection & moderator co‑pilot for Facebook Groups — powered by [`RAGCore‑X`](https://github.com/iii-cstiicdc/ragcore-x)**

![ScamShield banner](docs/assets/scamshield_banner.png)

<p align="center">
  <a href="https://github.com/iii-cstiicdc/scamshield-ai/actions"><img src="https://github.com/iii-cstiicdc/scamshield-ai/workflows/CI/badge.svg" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-proprietary-lightgrey.svg" /></a>
  <img src="https://img.shields.io/badge/status-alpha-yellow.svg" />
</p>

---

## 🚀 Project Vision

> *“Spot fraud in < 60 seconds and cut moderators’ workload in half.”*

ScamShield‑AI injects a proven Retrieval‑Augmented Generation (RAG) engine into the daily routine of Facebook‑Group moderators.
A **Chrome Extension** on the client side and an **official Facebook Webhook** on the server side work in tandem so that **every new post** is:

1. **Classified** by RAGCore‑X (risk score 0–1 & top‑k supporting cases).
2. **Labelled** with a red / yellow / green badge in the UI.
3. **Optionally auto‑replied** with a context‑aware warning.
4. **Logged** for daily digest & continuous re‑training.

### Success Metrics (PoC)

| Metric               | Target | Notes                              |
| -------------------- | ------ | ---------------------------------- |
| Recall (scam posts)  | ≥ 70 % | Measure on a 300‑post labelled set |
| End‑to‑end latency   | ≤ 60 s | From post creation to badge shown  |
| Manual review count  | −50 %  | Moderator self‑report during pilot |
| FB policy compliance | 100 %  | No use of deprecated Groups API    |

---

## 🏗  Architecture Overview

```text
┌─ Admin Browser ───────────────────────────┐                 ┌─ Cloud ─────────────────┐
│ Chrome Ext. (content‑script)             │                 │  fb_webhook Function    │
│  • DOM → /classify (fetch)              │───────────────► │  (FastAPI)             │
│  • WS overlay ◄── notify                │                 └────────┬─────────────────┘
└───────────────────────────────────────────┘                          ▼
                                                               ┌────────────────────┐
                                                               │  RAGCore‑X (all‑in)│
                                                               │  • Embedded Qdrant │
                                                               │  • Async queue     │
                                                               │  • Prompt builder  │
                                                               └────────────────────┘
```

> **No external Redis / Qdrant** are needed in PoC — RAGCore‑X boots a lightweight vector DB and queue in‑process.

---

## 🥇 MVP Scope (3‑Week PoC)

| Included                        | Description                                  | Effort |
| ------------------------------- | -------------------------------------------- | ------ |
| 🟥 Text‑only classification     | `/classify` endpoint → risk badge            | core   |
| 🟧 Admin‑side Chrome Extension  | DOM scrape, badge inject, Quick‑Reply button | core   |
| 🟨 Passive auto‑reply (Webhook) | Trigger only when post **@mentions** Page    | add‑on |
| 🟩 Daily email digest           | Simple cron + CSV attachment                 | add‑on |

**Deferred (post‑PoC)**: OCR on screenshots, SaaS billing plane, mobile Safari extension, one‑click retrain UI.

---

## ✨ Feature Highlights

* **Zero‑install back‑end** — `uvicorn app.main:app` starts the whole stack.
* **Dual ingestion** — bulk warm‑up via CLI *or* lazy on‑the‑fly indexing.
* **Shadow‑DOM overlay** — traffic‑light badge, modal with “Why risky” & 3 similar cases.
* **Rate‑aware auto‑reply** — only if risk ≥ 0.85 **and** post tags `@ScamShield AI`.
* **Daily heat‑map digest** — HTML + CSV via SendGrid / Line Notify.

---

## ⚙️ Quick Start (Local Dev)

```bash
# Clone & bootstrap
$ git clone https://github.com/iii-cstiicdc/scamshield-ai.git && cd scamshield-ai

# Backend
$ python -m venv .venv && source .venv/bin/activate
$ pip install -r backend/requirements.txt
$ cp .env.example .env  # fill in FB tokens
$ uvicorn app.main:app --reload  # starts RAGCore‑X & API on :8000

# Facebook webhook (ngrok → FB callback URL)
$ python -m backend.fb_webhook --port 9000

# Front‑end
$ cd extension && npm ci && npm run build  # dist/ folder
# Load unpacked at chrome://extensions
```

When you open the test group, new posts should light up in red / yellow / green in ≈ 4 seconds.

---

## 📨 Key API End‑points

### `POST /classify`

```json
{
  "text": "I can triple your crypto in one week …",
  "lang": "auto"  // zh, en, jp also accepted
}
```

Response:

```json
{
  "risk_score": 0.91,
  "label": "high",
  "explanation": "Matches investment‑scam pattern …",
  "similar_cases": [ {"title":"Crypto ROI 300%", "score":0.92} ]
}
```

*95‑percentile latency < 1 s (GPT‑4o) / 300 ms (local Llama‑3‑8B‑Int4).*

### `POST /ingest`

Bulk warm‑up (Phase 0)

```bash
curl -F file=@sample_posts.json -F project_id=scamshield http://localhost:8000/ingest
```

---

## 🛡 Risk & Mitigation

| Risk                              | Impact                | Mitigation                                                                                     |
| --------------------------------- | --------------------- | ---------------------------------------------------------------------------------------------- |
| **DOM selector breakage**         | Badges stop appearing | 3 fallback selectors + Playwright daily smoke test ; WS error alert                            |
| **FB anti‑automation rate‑limit** | Page token blocked    | Limit 2 req/s (webhook) & 5 req/min (extension cache) ; only auto‑reply on high‑risk + mention |
| **Groups API deprecation**        | Cannot post to group  | Use Page mention / admin Quick‑Reply ; keep URL‑scanner bot as backup                          |
| **False positives**               | User trust drops      | Badge shows “Not scam” button → feedback stored ; weekly retrain pipeline                      |
| **Image‑only scams**              | Miss recall           | Out‑of‑scope for MVP ; planned OCR Phase 2                                                     |
| **Policy compliance**             | Page suspension       | Extension only for admins ; auto‑messages disclose "AI assistant" ; data retention 30 days     |

---

## 🛣 Roadmap

### Phase Timeline (PoC)

| Week   | Milestone                     | Deliverable                                          |
| ------ | ----------------------------- | ---------------------------------------------------- |
| **W1** | Ingest API + seed 300 posts   | Qdrant ≥ 300 vectors ; `/classify` returns score     |
| **W2** | Chrome extension + risk badge | Live colour overlay ; Quick‑Reply button (manual)    |
| **W3** | Webhook auto‑reply + digest   | Comment bot & daily email ; demo script + KPI report |

### Beyond PoC

| Feature                         | ETA     | Notes                              |
| ------------------------------- | ------- | ---------------------------------- |
| OCR pipeline (Tesseract)        | 2025‑Q3 | Selective, risk ≥ 0.8 only         |
| One‑click retrain loop          | 2025‑Q3 | Feedback → re‑embed nightly        |
| SaaS control plane & billing    | 2025‑Q4 | Multi‑tenant RBAC, Stripe metering |
| Mobile Safari/WebView extension | 2025‑Q4 | Electron alt if WebExt blocked     |

---

## 🧪 Testing Matrix

* `pytest` — unit & contract tests (OpenAI, FB Graph mocked)
* `pnpm playwright test` — scroll feed, assert badge rendered in ≤ 5 s
* GitHub Action nightly: smoke DOM test against `facebook.com` dev build

---

## 🤝 Contributing

1. Fork → feature branch.
2. Run **both** `pytest` & `pnpm test`.
3. Sign CLA in `docs/CLA.md`.

---

## 📄 License

Proprietary Software License Agreement — © 2025 Institute for Information Industry (III), Cyber Security Technology Institute (CSTI).

Evaluation use permitted; contact [poplol0900@gmail.com](mailto:poplol0900@gmail.com).

---

Made with ❤️ in Taiwan — Powered by **RAGCore‑X**
