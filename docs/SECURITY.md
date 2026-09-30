# Security design & Aikido audit notes

Aikido's AI Code Audit checks for business-logic flaws, IDOR, authentication and authorisation problems. How each area is handled:

| Area | Risk | Mitigation | Where |
|---|---|---|---|
| Authentication | Forged or replayed tokens | HMAC-SHA256 signed tokens, constant-time compare, 8h expiry, key from `TTG_SECRET_KEY` (min 32 chars) | `backend/app/security.py` |
| Authentication | Passwordless login in production | `/api/auth/demo-login` returns 404 unless `TTG_DEMO_LOGIN=true`; rate-limited; inactive users refused | `main.py` |
| Authorisation | Querying another country's knowledge | `require_country` on every route; admins only have cross-country access | `main.py` |
| IDOR | Reading or flagging a document via a guessed ID | Document must belong to the requested (authorised) country; unknown and out-of-scope documents both return 404 | `require_document_in_country` |
| IDOR | Reading or marking other users' alerts | Notifications filtered by `recipient == token user` | `/api/notifications*` |
| Identity spoofing | Posting a flag "as" someone else | Reporter taken from the token; unknown body fields rejected (`extra="forbid"`) | `ConflictIn` |
| Business logic | Tanking a competitor document's trust by spamming flags | One open flag per user per document (409), 10 flags/hour/user, trust floor of 5% | `flag_conflict` |
| Business logic | Owner self-flagging / self-dealing | Owners can't flag their own document | `flag_conflict` |
| Business logic | Silencing contradictions by re-verifying blindly | Only owner / country expert / admin may verify, and must set `reviewed_contradictions=true` | `verify` |
| Input validation | Injection / oversized payloads | Pydantic length limits, regex-validated IDs and channels, country enum | models in `main.py` |
| Info disclosure | Stack traces, API schema | Global exception handler, `/docs` only when `TTG_ENV=development` | `main.py` |
| Browser | XSS / clickjacking | React escaping, no `dangerouslySetInnerHTML`, CSP + `X-Frame-Options: DENY`, token kept in memory only (no localStorage) | `next.config.ts` |
| Secrets | Keys in the repo | `.gitignore` covers `.env*`; only `.env.example` templates are committed | repo root |

## Audit log

| Run | Date | Findings | Notes |
|---|---|---|---|
| Baseline | _fill in_ | _fill in_ | screenshot: `docs/aikido-before.png` |
| After fixes | _fill in_ | _fill in_ | screenshot: `docs/aikido-after.png` |
