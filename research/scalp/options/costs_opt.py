"""Option BUYING cost model (premium turnover). RATES CHANGE - verify STT/exchange charges before trusting results."""

from dataclasses import dataclass


@dataclass
class OptionCostModel:
    brokerage_flat: float = 20.0
    stt_sell_pct: float = 0.001  # on sell premium. VERIFY (raised in Oct 2024; may have changed since)
    exch_pct: float = 0.0003503  # NSE options, on premium turnover. VERIFY (BSE differs)
    sebi_pct: float = 0.000001
    stamp_buy_pct: float = 0.00003
    gst: float = 0.18
    slippage_rs: float = 0.10  # per fill, in premium rupees: half the bid-ask spread you cross. Wider when illiquid

    def side(self, prem: float, qty: int, is_buy: bool) -> float:
        turn = prem * qty
        exch, sebi = self.exch_pct * turn, self.sebi_pct * turn
        gst = self.gst * (self.brokerage_flat + exch + sebi)
        return (self.brokerage_flat + exch + sebi + gst
                + (0.0 if is_buy else self.stt_sell_pct * turn) + (self.stamp_buy_pct * turn if is_buy else 0.0))

    def round_trip(self, entry: float, exit_: float, qty: int) -> float:
        return self.side(entry, qty, True) + self.side(exit_, qty, False)

    def breakeven_pts(self, prem: float = 150.0, qty: int = 75) -> float:
        """Premium points an option must gain just to pay fees + spread (round trip)."""
        return self.round_trip(prem, prem, qty) / qty + 2 * self.slippage_rs
