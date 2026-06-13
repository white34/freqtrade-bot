# Devlog 01 — Building a Systematic Trading Bot

**Date:** June 13, 2026

## The why

I've always been interested in markets but what drew me to algorithmic
trading specifically was the idea that you could remove emotion from the
equation entirely and replace it with a testable, falsifiable system.
Either the edge exists in the data or it doesn't.

## What I built

The bot runs on Freqtrade, an open source crypto trading framework, on
Binance USDT-M futures. Everything is Dockerised and runs locally on my
laptop. The core strategy is a mean-reversion long that enters dip
positions in altcoins when BTC is in a confirmed uptrend, using RSI,
Bollinger Bands, and an ADX regime filter to avoid trading in choppy
conditions.

The research process was more rigorous than I expected going in. Every
strategy candidate goes through a multi-gate evaluation: full history
backtest, out-of-sample holdout, walk-forward validation across multiple
windows, per-pair concentration checks, and a fee sensitivity re-run at
double the maker rate. Anything that fails a gate gets documented and
dropped, not iterated on endlessly.

## Results

The current live system backtests at around 715% over 5 years across 39
pairs, with out-of-sample results of roughly 188% CAGR over the most
recent 23 months. A Monte Carlo bootstrap of the out-of-sample trade
history gives a median 1-year CAGR around 79% with a 2% chance of a
losing year. The bot is currently in dry-run to validate that live
behaviour matches backtest expectations before any real capital goes in.

## Key lessons

The biggest lesson was around leverage semantics. Freqtrade applies
stoploss and ROI values to the leveraged profit ratio, not the price
move. A stoploss of -7% at 5x leverage is actually a -1.4% price move.
Every stop in the original version of the bot was sized wrong because of
this. Catching it and rebuilding the risk model from scratch was the most
important thing I did on this project.

The second lesson was that hyperopt actively makes things worse if used
before you have a real edge. A 150-epoch optimisation run produced a
strategy 4x worse out-of-sample than the hand-tuned defaults. Hyperopt
now only runs after a candidate passes all evaluation gates on its
original parameters.

## What's next

Observing the dry-run for 4 to 6 weeks and comparing live trade
distribution against backtest expectations before considering real
capital. Also researching a funding-rate carry strategy as a second
uncorrelated bot.
