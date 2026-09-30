# Demo video script (target 2:45, under 3:00)

About 410 spoken words at roughly 150 wpm. The **VO** lines are the text to paste into ElevenLabs; **SCREEN** tells you what to record.

---

### 0:00 – 0:20 · The moment of doubt
**SCREEN:** Empty dashboard, headline "A search returns ten answers. Which one can you trust?"

**VO:** An urgent client question lands on a payroll consultant's desk. The answer exists somewhere, in a policy, an old handover note, a Teams thread. Finding information is easy now. Knowing whether you can rely on it is the hard part. This is Temporal Trust Graph.

### 0:20 – 0:55 · One question, one country
**SCREEN:** Sign in as Greet Maes (BE). Ask "holiday pay". Hover the "3 from other countries filtered out" label.

**VO:** Greet is a Belgian consultant asking about double holiday pay. Behind the scenes, all our knowledge is a graph: documents, experts, countries, Teams conversations and verification events, all connected. First, the graph is scoped strictly to Belgium. The Dutch holiday allowance document shares the same keywords, but it gets filtered out before scoring, so it can't lend or take trust.

### 0:55 – 1:40 · Trust you can read
**SCREEN:** Top card (score 98), meters, open "Why this score?". Scroll to the legacy card (score 1) with its red warning. Point at the dashed red edge in the graph.

**VO:** The best answer scores ninety-eight, and you can see why. It was verified twelve days ago. Anna, an active expert, owns it. Two colleagues endorsed it, which gives it high centrality in the Belgian graph. Every signal is a line you can read, with no black box. Below it are the legacy handover notes. Nobody owns them, nobody has verified them in over two years, and last week someone in the payroll channel said the rule inside is outdated. That Teams message is a Contradicted By edge in the graph, and it decays the score to almost zero. The dashboard doesn't hide this document. It warns you, clearly, not to rely on it.

### 1:40 – 2:15 · Closing the loop
**SCREEN:** Click "meal vouchers" → Flag conflict → fill in channel and text → submit. Toast shows trust 73 → 45.

**VO:** Knowledge changes faster than documents. When Greet hears in Teams that the meal voucher rules changed, she flags it right here. The conflict becomes a new edge in the graph. Trust drops from seventy-three to forty-five on the spot, and the owner gets an alert.

### 2:15 – 2:35 · The owner responds
**SCREEN:** Switch user to Anna Peeters → alert banner → Re-verify → score rises; the contradiction shows as resolved.

**VO:** Anna sees the alert, checks the change and re-verifies. Because trust is temporal, contradictions older than the latest verification count as resolved, and the score recovers. If a document has no owner, the alert goes to the country's experts, so nothing falls through the cracks.

### 2:35 – 2:50 · Secure by design
**SCREEN:** Aikido before/after screenshots, then the README architecture diagram.

**VO:** Trust also means security. Every route checks your country and your identity, which blocks flag spamming and cross-country data access. We validated all of it with Aikido's AI Code Audit.

### 2:50 – 3:00 · Close
**SCREEN:** Dashboard with the graph.

**VO:** Temporal Trust Graph. From "I found something" to "I understand why I can rely on it."
