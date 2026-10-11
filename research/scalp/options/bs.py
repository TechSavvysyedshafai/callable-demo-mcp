"""Black-Scholes European option price and delta (no dividends). Model-based premiums only."""

from math import erf, exp, log, sqrt


def _cdf(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def price(S: float, K: float, T: float, iv: float, is_call: bool, r: float = 0.065) -> float:
    if T <= 0 or iv <= 0:
        return max(S - K, 0.0) if is_call else max(K - S, 0.0)
    d1 = (log(S / K) + (r + 0.5 * iv * iv) * T) / (iv * sqrt(T))
    d2 = d1 - iv * sqrt(T)
    if is_call:
        return S * _cdf(d1) - K * exp(-r * T) * _cdf(d2)
    return K * exp(-r * T) * _cdf(-d2) - S * _cdf(-d1)


def delta(S: float, K: float, T: float, iv: float, is_call: bool, r: float = 0.065) -> float:
    if T <= 0 or iv <= 0:
        return float(S > K) if is_call else -float(S < K)
    d1 = (log(S / K) + (r + 0.5 * iv * iv) * T) / (iv * sqrt(T))
    return _cdf(d1) if is_call else _cdf(d1) - 1.0
