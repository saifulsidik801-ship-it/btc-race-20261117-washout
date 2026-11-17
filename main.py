"""Washout Reversion bot for make.fun btc-race-24h-20261117-0603.

Race a BTC trading bot live for 24 hours: one asset (CBBTC, Coinbase Wrapped
BTC on Solana, quoted in USDC), $1,000 paper money, long only, 1-minute bars,
orders decided on one batch fill at the next bar's open. The bot speaks
agent-fun/bars-replay/v1: hello once, then one batch per bar, one reply per
batch echoing its seq, with the orders decided on that bar.

Strategy — reconstructed from the top 10 of the previous race
(btc-race-24h-20261115-0828, see top1-push/btc-race-top10-reconstruction.md):
the whole top 10 was ONE trade each. The winners bought the completed
washout (the late flush low, ~$63,940) and held it to the close (+1.68%),
while partial early exits donated $1.20-$2.40. The winning hold was ~2 hours,
not 20 — the move came in the window's last 3 hours, and the trigger (below
$65,000) simply never fired during the first 21 choppy hours. So the rule is
RELATIVE, never an absolute price level fitted to one window:

  1. TRIGGER: the close sits at least DD_ARM below the trailing 240-bar
     high (a washout) AND has recovered at least REC_PCT above the trailing
     60-bar low, with that low inside the last REC_WIN bars (the washout is
     complete and momentum has turned). Buy FULL size.
  2. HOLD: to the window close, with a trailing stop TRAIL_PCT below the
     post-entry peak to lock the rip. Exit on recovery exhaustion, never on
     a small fitted take-profit.
  3. ONE trade per washout: after an exit, wait COOLDOWN bars before
     re-entering, so chop cannot bleed the bot on repeated small bounces.
  4. Do not trade a sub-1% expected move: a full-size round trip costs
     ~26 bps in fee, slippage and impact, so a small capture is eaten.

Determinism: every decision is a pure function of the closes seen so far.
No wall clock, no environment, no randomness, no dict-order dependence.
Two runs on the same bars produce the same orders, byte for byte.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

import makefun_bars

SYMBOL = "CBBTC"

# Tunable rule parameters. The grid search over the dev window plus a second
# window shape picked these values; neighbours score near the top too, so the
# fit is a plateau, not a knife edge.
PARAMS = {
    "dd_arm": 0.018,       # washout: close this far below trailing 240-bar high
    "rec_pct": 0.003,      # completion: close this far above trailing 60-bar low
    "rec_win": 15,         # the 60-bar low must be within this many bars
    "trail_pct": 0.007,    # trailing stop below the post-entry peak
    "cooldown": 120,       # bars to wait after an exit before re-entering
    "max_slip_bps": 150,   # max slippage vs the latest close, per order
    "peak_win": 240,       # trailing-high window (bars)
    "low_win": 60,         # trailing-low window (bars)
}

# Per-run state, reset by on_hello. All ints; closes are price_scale 5.
_closes = []
_last_t = -1
_peak_since_entry = 0
_cool_until = -1


def on_hello(state):
    """Reset per-run state when the hello arrives."""
    global _closes, _last_t, _peak_since_entry, _cool_until
    _closes = []
    _last_t = -1
    _peak_since_entry = 0
    _cool_until = -1


def on_batch(state, batch):
    """Decide the orders for this batch: one reply, zero or one order."""
    global _last_t, _peak_since_entry, _cool_until
    if state.warming_up:
        return []
    bar = state.latest.get(SYMBOL)
    if bar is None:
        return []
    t = state.t
    if t <= _last_t:
        return []
    _last_t = t
    close = state.close(SYMBOL)
    if close is None or close <= 0:
        return []
    _closes.append(close)

    p = PARAMS
    holding = state.positions.get(SYMBOL)
    in_pos = holding is not None and holding.qty > 0

    if in_pos:
        # Hold to the close; the trailing stop locks the rip.
        if close > _peak_since_entry:
            _peak_since_entry = close
        if _peak_since_entry > 0 and close <= _peak_since_entry * (1.0 - p["trail_pct"]):
            _cool_until = state.seq + p["cooldown"]
            _peak_since_entry = 0
            return [{
                "side": "sell",
                "symbol": SYMBOL,
                "qty": holding.qty,
                "max_slippage_bps": p["max_slip_bps"],
            }]
        return []

    # Flat: look for a completed washout.
    if len(_closes) < p["low_win"]:
        return []
    if state.seq <= _cool_until:
        return []
    window = _closes[-p["peak_win"]:]
    peak = max(window)
    lows = _closes[-p["low_win"]:]
    low = min(lows)
    # Age (in bars) of the low's last occurrence: 0 means the low IS this bar.
    low_age = lows[::-1].index(low)
    dd = (peak - close) / peak
    rec = (close - low) / low
    if dd >= p["dd_arm"] and rec >= p["rec_pct"] and low_age <= p["rec_win"]:
        notional = min(state.cash, state.weight_room(SYMBOL))
        if notional >= 1_000_000:  # at least 1 USDC
            _peak_since_entry = close
            return [{
                "side": "buy",
                "symbol": SYMBOL,
                "notional_quote_units": notional,
                "max_slippage_bps": p["max_slip_bps"],
            }]
    return []


if __name__ == "__main__":
    makefun_bars.run(on_batch, on_hello=on_hello)
