# Builderbase submission text

## Project description (Overview)

**Temporal Trust Graph: find it, understand it, trust it.**

When an SD Worx consultant asks a question, search returns several answers: a recently verified policy, a handover note with no owner, a document for another country and a contradicting Teams message. Temporal Trust Graph models that knowledge as a graph (documents, experts, countries, Teams chats and verification events) and computes trust from the graph's topology and timeline instead of keyword match.

A query is first scoped strictly to one country, so trust can't leak across borders. A personalised PageRank then lets trust flow from active experts and fresh verifications into the documents they own, endorse or verify. Freshness decays over time, and missing or departed owners are penalised. Every `Contradicted_By` edge from a Teams chat decays the score exponentially until the owner re-verifies. The dashboard shows each score with a plain-language "why", prominent warnings for unowned or contradicted documents, the country subgraph, and the experts to ask when documents fall short. Anyone can flag a Teams contradiction. Trust drops right away and the owner, or the country experts for orphaned documents, gets an alert, closing the loop between conversations and documentation.

Built with FastAPI + NetworkX and Next.js, security-hardened against Aikido's AI Code Audit (country-scoped authorisation, IDOR-safe resources, anti-abuse rules for flagging and verification).

## Fields
- GitHub repo: `https://github.com/<you>/temporal-trust-graph`
- Video link: `<YouTube unlisted / Loom / Drive link, viewable by anyone>`
- Screenshots: `docs/aikido-before.png`, `docs/aikido-after.png`
