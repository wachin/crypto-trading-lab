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

### volatility

**Definition:** How much prices move up and down over a period of time.

**In simple words:** High volatility = big price swings. Low volatility = prices stay relatively flat. High volatility means both bigger potential gains and bigger potential losses.

**Warning:** High volatility strategies can lose more than expected.

### strategy

**Definition:** A set of rules that tells you when to buy and when to sell.

**In simple words:** A strategy removes emotion from trading. Example: "Buy when the 5-period moving average crosses above the 20-period moving average; sell when it crosses below."

**Warning:** No strategy works in all market conditions.

### backtesting

**Definition:** Running a strategy against historical data to see how it would have performed.

**In simple words:** Like a flight simulator for trading. You test your strategy without risking real money. But remember: past performance doesn't guarantee future results.

**Warning:** Backtests can be misleading if they ignore fees, slippage, or look-ahead bias.

### paper trading

**Definition:** Trading with simulated money using real market data.

**In simple words:** Real trading without real risk. It's a step between backtesting and real trading. The application is set up this way by default.

**Warning:** Paper trading doesn't capture every real-world condition like slippage or liquidity.

### drawdown

**Definition:** The fall of your account value from its highest point to a following low, usually shown as a percentage.

**In simple words:** Imagine a graph of your money. A drawdown is the ugliest valley after any peak: "from my best moment, I was down X%." A strategy can make money overall and still have terrifying valleys.

**Warning:** Deep drawdowns are what make real traders abandon otherwise sound strategies. Look at them before you look at profits.

### position sizing

**Definition:** How much of your capital to risk on each trade.

**In simple words:** If you have $10,000 and use 1% position sizing, you risk $100 per trade. Proper sizing helps you survive a series of losses without blowing up your account.

**Warning:** Oversizing (risking too much per trade) is the fastest way to lose money.

### out-of-sample

**Definition:** Data that was NOT used to build or tune your strategy.

**In simple words:** You train your strategy on one set of data, then test it on completely new data. This tells you if it really has edge or just memorized patterns.

**Warning:** A strategy that only works on training data is overfit and will fail in real trading.

### overfit

**Definition:** When a strategy has learned the noise in historical data rather than a real pattern.

**In simple words:** Like a student who memorizes old exam answers instead of learning the material. It will score well on old exams but fail on new ones.

**Warning:** Overfit strategies look great in backtests but fail in real trading.


### liquidity

**Definition:** How easily you can buy or sell without moving the price much.

**In simple words:** High liquidity means you can trade big size and the price stays the same. Low liquidity means even a small trade moves the price.

**Warning:** In illiquid markets, your market order might execute at a much worse price than you saw.

### latency

**Definition:** The delay between sending an order and the exchange receiving it.

**In simple words:** Time it takes for your signal to travel across the internet to the exchange. In high-frequency environments, milliseconds matter.

**Warning:** In a fast-moving market, latency can mean you buy or sell after the price has already moved.

### fill

**Definition:** The actual execution of a trade.

**In simple words:** You sent an order; the exchange said "okay" and swapped your money for the asset. That swap is the fill.

**Warning:** In a live market, orders sometimes don't fill because the price moves away before you reach it.

### backtesting bias

**Definition:** Errors in backtest results caused by incorrect assumptions.

**In simple words:** If your backtest uses future data to make decisions (look-ahead bias), it shows profits that would never be real.

**Warning:** Always check that your strategy logic only uses data available *at the time* of the signal.

### latency

**Definition:** The delay between sending an order and the exchange receiving it.

**In simple words:** Time it takes for your signal to travel across the internet to the exchange. In high-frequency environments, milliseconds matter.

**Warning:** In a fast-moving market, latency can mean you buy or sell after the price has already moved.

### fill

**Definition:** The actual execution of a trade.

**In simple words:** You sent an order; the exchange said "okay" and swapped your money for the asset. That swap is the fill.

**Warning:** In a live market, orders sometimes don't fill because the price moves away before you reach it.

### backtesting bias

**Definition:** Errors in backtest results caused by incorrect assumptions.

**In simple words:** If your backtest uses future data to make decisions (look-ahead bias), it shows profits that would never be real.

**Warning:** Always check that your strategy logic only uses data available *at the time* of the signal.


### order size

**Definition:** The quantity of units to trade in a single transaction.

**In simple words:** If you have $1,000 and want to risk 1% per trade, and the stock price is $100, your order size would be 10 shares. Proper order size ensures that a single trade doesn't overly impact your portfolio.

**Warning:** Overly large order sizes can lead to significant losses if the trade moves against you, and can also cause slippage issues in illiquid markets.

### pi

**Definition:** A mathematical constant approximately equal to 3.14159, representing the ratio of a circle's circumference to its diameter.

**In simple words:** Pi is just a number that shows up in all sorts of unexpected places in mathematics and physics, including in formulas for the period of a pendulum, the probability of certain random events, and in the calculation of circle areas.

**Warning:** Don't confuse this with "pie," the delicious dessert.

### circuit breaker

**Definition:** A mechanism that automatically halts trading when certain adverse conditions are met.

**In simple words:** Like a household electrical circuit breaker, if the system detects extreme market conditions or strategy losses, it automatically stops trading to prevent further losses.

**Warning:** Circuit breakers can sometimes halt trading during momentary glitches, so it's important to understand the specific conditions that trigger them.

### market order

**Definition:** An order to buy or sell immediately at the best available current price.

**In simple words:** A market order says "I want to buy/sell right now, no matter what the price is." It's the fastest way to get in or out of a position, but you might not get the exact price you saw a moment ago.

**Warning:** Market orders in illiquid markets can result in very poor fill prices due to slippage.

### limit order

**Definition:** An order to buy at or below a specific price, or to sell at or above a specific price.

**In simple words:** A limit order says "I want to buy, but only if the price is $X or lower." It gives you price control, but the order might not execute if the price never reaches your limit.

**Warning:** Limit orders can leave you unfilled, meaning you don't enter or exit the position, which can be frustrating if you're trying to capitalize on a fast-moving move.

