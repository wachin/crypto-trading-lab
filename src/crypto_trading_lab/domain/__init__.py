"""Domain layer: models shared by every exchange adapter and engine.

Rules from ROADMAP.md chapter 7 that this module enforces:

- ``Decimal`` for money, prices, quantities, commissions, and balances.
- UTC timestamps internally; local timezone only for presentation.
- Dataclasses for value-like records; no ``float`` in critical fields.
"""
