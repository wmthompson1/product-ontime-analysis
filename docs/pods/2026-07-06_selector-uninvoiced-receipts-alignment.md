# Selector output alignment — Uninvoiced Receipts → three_way_match (2026-07-06)

**Question:** Is the Selector v1.0 output (Perspective = Payables, Ground-truth query = Uninvoiced Receipts → "10 bound mappings in `three_way_match`", first card `map-twm-invoice-line`) aligned with the selection?

**Answer: Yes — the output is aligned.** Here is the exact chain it followed (nothing is guessed at any step):

1. **The selection:** Tags = Payables, Ground-truth query = **Uninvoiced Receipts** — the Selection context echoes both correctly.
2. **The binding:** the governed query file carries an explicit marker (`-- Binding: payables_uninvoicedreceipts_20260706_000003`), and the committed bridge (`poc/ontop-ontology-poc/binding_bridge.json`) maps that key to the **`three_way_match`** showcase ontology.
3. **The output:** "Uninvoiced Receipts → 10 bound mappings in `three_way_match`" — that's the entire three-way-match ontology, because the bridge binds at the **ontology level**, not per-leg. All three procurement queries (Orders Received, Orders Unreceived, Uninvoiced Receipts) intentionally resolve to the same 10 mappings, since each query is one lens on the same PO-line ↔ receipt-line ↔ invoice-line match.

## Why the first card is the invoice-line mapping

The card shown first, `map-twm-invoice-line` (Mints `:InvoiceLine`, "Leg 3"), might look off-topic at first glance — it's about invoices while the query is about *missing* invoices. But it's actually the defining leg for this query: its own comment says it — *"a receipt line with no such incoming link is an Uninvoiced Receiver."* Uninvoiced Receipts is precisely the set of receipt lines where that leg-3 link is absent. The receipt-line mapping (leg 2) is further down among the 10 cards.

## Verdict

Selection → binding key → bridge → ontology all check out. The only cosmetic quirk is card order — mappings appear in the order they're defined in the ontology file, not by relevance to the chosen query. Reordering so the most on-topic leg (the receipt line) appears first for Uninvoiced Receipts is a possible future tweak, not a defect.
