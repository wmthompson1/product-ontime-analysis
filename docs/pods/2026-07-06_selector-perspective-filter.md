# Selector tab — perspective filter as searchable multi-select

*Saved from chat, 2026-07-06.*

The Selector tab now matches what you asked for: the perspective filter is a search-style multi-select dropdown — type a few letters (e.g. "cust") and it narrows to matching perspectives, pick as many as you want, and each shows as a removable chip. Below it, the 5 concrete filter fields stay in one horizontal row: Table → Column → Concept → Intent → Ground-truth query.

Verified after the restart: selecting Payables + Quality together narrows tables to certification, payables, purchase_order, receiving; clearing the filter restores all 26 tables.

## Context from the same session

Earlier in the session the tag vocabulary itself was corrected: the filter now uses the 15 stakeholder perspectives from `schema_perspectives` (Quality, Payables, Work_Orders, General_Ledger, Receivables, CRM, Manufacturing, Inventory_Transactions, Customer_Order, Demand_Forecast, Engineering, Parts, Visual_Admin, Finance, Customer) — the same vocabulary and order as the Define Relationship category chips — replacing the three abstract intent categories.

All three filters flow through the real perspective links in the semantic layer:

- **Tables** — only tables whose mapped columns lead to a concept that perspective uses (e.g. Quality → certification, purchase_order, receiving; Payables → payables, purchase_order, receiving; Inventory_Transactions → customer_order_line, inventory_transaction, part, po_line).
- **Concepts** — narrowed to that perspective's concepts (`schema_perspective_concepts`).
- **Intents** — narrowed to intents linked to that perspective (`schema_intent_perspectives`).

Coverage gaps are surfaced honestly: where a chain genuinely runs dry the summary panel says so — for example Quality → CertificationType currently has no elevating intent inside Quality, and the panel explains that instead of showing a blank dropdown.
