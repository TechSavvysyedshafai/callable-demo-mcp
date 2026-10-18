"""Indian index-futures cost model. Statutory/exchange rates below match Upstox's published charges page as read on
2026-10-18 (STT 0.05% on futures sell side from 1 Apr 2026; NSE futures transaction charge 0.00183% from 1 Mar 2026).
STT/exchange/SEBI/stamp are the same at any broker; brokerage differs. Rates change: re-verify, and verify lot size."""

from dataclasses import dataclass


@dataclass
class CostModel:
    lot_size: int = 75  # VERIFY: NSE revises this
    brokerage_flat: float = 20.0  # Rs per executed order, or ...
    brokerage_pct_cap: float = 0.0003  # ... 0.03% of turnover, whichever is lower
    stt_sell_pct: float = 0.0005  # futures, sell side, from 1 Apr 2026 (was 0.0002)
    exch_pct: float = 0.0000183  # NSE futures transaction charge 0.00183% (from 1 Mar 2026)
    sebi_pct: float = 0.000001  # Rs 10 per crore
    stamp_buy_pct: float = 0.00002  # buy side
    gst: float = 0.18  # on brokerage + exchange + SEBI
    slippage_pts: float = 0.5  # index points per market fill (the engine applies it)

    def side(self, px: float, qty: int, is_buy: bool) -> float:
        turnover = px * qty
        brok = min(self.brokerage_flat, self.brokerage_pct_cap * turnover)
        exch, sebi = self.exch_pct * turnover, self.sebi_pct * turnover
        gst = self.gst * (brok + exch + sebi)
        stt = 0.0 if is_buy else self.stt_sell_pct * turnover
        stamp = self.stamp_buy_pct * turnover if is_buy else 0.0
        return brok + exch + sebi + gst + stt + stamp

    def round_trip(self, entry: float, exit_: float, direction: int, qty: int) -> float:
        buy, sell = (entry, exit_) if direction > 0 else (exit_, entry)
        return self.side(buy, qty, True) + self.side(sell, qty, False)

    def breakeven_pts(self, px: float, qty: int | None = None) -> float:
        """Index points a trade must move just to pay fees + slippage."""
        qty = qty or self.lot_size
        return self.round_trip(px, px, 1, qty) / qty + 2 * self.slippage_pts
