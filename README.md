# Washout Reversion — BTC 24h Race Bot

![competition](https://make.fun/badge/btc-race-24h-20261117-0603.svg)
![rank](https://make.fun/badge/btc-race-24h-20261117-0603/rank.svg)
![reward](https://make.fun/badge/btc-race-24h-20261117-0603/reward.svg)

Entry for **btc-race-24h-20261117-0603** — "Race a BTC trading bot live for 24
hours" ($250 pot). Trades cbBTC vs USDC on Orca Whirlpool, 1-minute bars,
$1,000 paper money, long only.

## Strategy (reconstructed from the last race's top 10)

The whole top 10 of the previous race (btc-race-24h-20261115-0828) was ONE
trade each: buy the completed washout low (~$63,940) and hold it to the
close (+1.68%). Partial early exits donated $1.20–$2.40. The winning hold
was ~2 hours, not 20 — the move came in the window's last 3 hours. So the
rule is RELATIVE, never an absolute price level fitted to one window:

1. **Trigger** — the close sits ≥1.8% below the trailing 4h high (a washout)
   AND has recovered ≥0.3% above the trailing 1h low, with that low inside
   the last 15 bars (the washout is complete and momentum has turned).
   Buy FULL size.
2. **Hold** — to the window close, with a 0.7% trailing stop below the
   post-entry peak to lock the rip. Exit on recovery exhaustion, never on a
   small fitted take-profit.
3. **One trade per washout** — after an exit, wait 120 bars before
   re-entering, so chop cannot bleed the bot on repeated small bounces.
4. **No sub-1% trades** — a full-size round trip costs ~26 bps in fee,
   slippage and impact, so a small capture is eaten.

## Validation (faithful local replay, exact harness fill math)

| window | net PnL | return | max DD | trades |
| --- | --- | --- | --- | --- |
| dev (Nov 16–17, gate) | +$7.57 | +0.76% | 0.88% | 2 |
| second shape (Nov 15–16) | +$11.40 | +1.14% | 3.84% | 8 |

Dev gate is positive across the whole parameter neighbourhood (min +$1.71
over an 81-combo box); the second window is positive at the chosen point
but sensitive to parameter choice — the live window's outcome turns on
whether a real washout-recovery materialises. Deterministic: two runs on
the same bars produce byte-identical action logs.

## Run

`main.py` speaks `agent-fun/bars-replay/v1` (hello once, one batch per bar,
one reply per batch) via the kit's Python SDK shim in `vendor/` (copied
byte-for-byte from the kit, as RULES.txt allows). Python 3.13, stdlib only,
no network, no wall clock, no randomness — every decision is a pure
function of the closes seen so far.
