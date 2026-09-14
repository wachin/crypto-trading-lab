# Glossary — Crypto Trading Lab (English)

Plain-language definitions for every term a beginner will meet. Each
entry gives a short definition, an explanation in simple words, and —
where it matters — a warning. Terms link to the Learning Center
lessons and to `docs/en/beginners/00-start-here.md`.

## The essential fifteen

### cryptocurrency

**Definition:** Digital money that works without a bank or government
in the middle, secured by cryptography.

**In simple words:** Normal money lives in a bank's ledger. A
cryptocurrency lives in a public ledger (a *blockchain*) that
thousands of computers keep and verify together. Nobody can quietly
edit it.

**Example:** Bitcoin is the best-known cryptocurrency.

**Warning:** Cryptocurrencies can be extremely volatile — their price
can rise or fall by large percentages in a single day.

### Bitcoin

**Definition:** The first cryptocurrency (2009), with a fixed maximum
supply of 21 million units.

**In simple words:** Often called "digital gold" because, like gold,
nobody can just print more of it. Each unit is called a bitcoin (BTC).

### exchange

**Definition:** A website or platform where people buy and sell
cryptocurrencies.

**In simple words:** Like a marketplace — buyers offer what they'll
pay, sellers offer what they'll accept, and the exchange matches them.

**Warning:** Exchanges can be hacked, can freeze withdrawals, or can
go bankrupt. Never keep more on an exchange than you actively intend
to trade. This application works *without* an exchange account.

### trading pair

**Definition:** The two assets being exchanged, written as
`BASE/QUOTE`, e.g. `BTC/USDT`.

**In simple words:** When you "buy BTC/USDT" you are using USDT to buy
BTC. The price tells you how much quote one unit of base costs — like
a price tag in a foreign shop.

### candle

**Definition:** One bar on a candlestick chart summarizing a time
interval: open, high, low, and close (plus volume).

**In simple words:** Each candle is a small story about one slice of
time — where the price started, how high and low it wandered, and
where it stopped. Green usually means it went up; red, down.

### volume

**Definition:** How much of the asset changed hands during the
candle's time interval.

**In simple words:** Volume is how crowded the market was. A price
move on huge volume is like a crowd running — worth noticing. The
same move on tiny volume may be noise.

**Warning:** Zero or missing volume makes a candle much less
trustworthy.

### order

**Definition:** An instruction to buy or sell an asset.

**In simple words:** "Buy 0.001 BTC at no more than $60,000" is an
order. The two classic types are *market orders* (buy/sell right now
at whatever price) and *limit orders* (only at your price or better).

### fee

**Definition:** The commission the exchange charges for each trade.

**In simple words:** Every buy and sell costs a small percentage of
the trade. Small — but they add up, and backtests that ignore fees
are lying to you. This application always counts them.

### slippage

**Definition:** The difference between the price you expected and the
price you actually got.

**In simple words:** You click "buy at $60,000" but by the time your
order lands, the price moved and you paid $60,004. That gap is
slippage. Thin, fast markets produce more of it.

### volatility

**Definition:** How much and how quickly a price moves around.

**In simple words:** High volatility is a rollercoaster; low
volatility is a train on flat ground. Big swings mean both bigger
possible gains and bigger possible losses — in crypto, mostly bigger
losses for beginners.

### strategy

**Definition:** A set of explicit, testable rules that decides when to
buy and when to sell.

**In simple words:** "If the price crosses above its 50-candle
average, buy; if it crosses below, sell." A strategy removes hope and
fear from the moment of decision — the rules decide, not your
emotions.

**Warning:** In this application, strategies *propose*; the risk
manager *disposes*. A strategy can never bypass risk control.

### backtesting

**Definition:** Testing a strategy on historical data to see how it
*would have* behaved.

**In simple words:** Rewind the market's history, let your rules run
on it, and see what would have happened — including fees and mistakes.

**Warning:** A good backtest does not prove the future will be the
same. Backtests can lie in many ways (see the lessons on *look-ahead
bias* and *overfitting*).

### paper trading

**Definition:** Practicing with simulated money on real or replayed
market data.

**In simple words:** The flight simulator of trading. You take every
decision a real trader would, but with fake money, so every mistake
is a free lesson instead of a real loss.

**Warning:** Paper trading removes real-world pressure (your own
fear and greed) — and those emotions are often the hardest opponent
you will face.

### risk

**Definition:** The possibility of losing part or all of the money
you put into a position.

**In simple words:** Risk is not a bad word; ignoring it is. Risk
management means deciding, *before* you trade, how much you can
afford to lose — and enforcing that limit.

### drawdown

**Definition:** The fall of your account value from its highest point
to a following low, usually shown as a percentage.

**In simple words:** Imagine a graph of your money. A drawdown is the
ugliest valley after any peak: "from my best moment, I was down X%."
A strategy can make money overall and still have terrifying valleys.

**Warning:** Deep drawdowns are what make real traders abandon
otherwise sound strategies. Look at them before you look at profits.

---

## Further reading

- Start here: `00-start-here.md`
- The Learning Center (inside the application) expands each term with
  examples, quizzes, and links to the relevant screens.
- Spanish translation of this glossary will live at
  `docs/es/beginners/glosario.md` once the English version is stable.
