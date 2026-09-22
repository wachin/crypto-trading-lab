"""Bundled learning curriculum (ROADMAP.md chapters 23 and 80).

Three levels, written in the "For Dummies" voice the roadmap asks for:
friendly, patient, concrete, and honest about risk. The content is
bundled data, not UI strings, so it works fully offline; the interface
chrome around it is translated with ``self.tr()``.

* **Level 1 — Trading from zero**: what money, crypto, markets, orders,
  fees, risk and survival are.
* **Level 2 — Practical trading**: the vocabulary and mechanics a
  trader actually uses day to day.
* **Level 3 — Quantitative research**: how to test an idea honestly and
  how to know when the evidence is not there.

Every lesson ends with one quiz question and a plain explanation.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "QuizQuestion",
    "LessonContent",
    "LEVEL_NAMES",
    "CURRICULUM",
    "lessons_for_level",
    "get_lesson",
    "total_lessons",
    "LEVELS",
]

LEVELS: tuple[int, ...] = (1, 2, 3)

LEVEL_NAMES: dict[int, str] = {
    1: "Level 1 — Trading from zero",
    2: "Level 2 — Practical trading",
    3: "Level 3 — Quantitative research",
}


@dataclass(frozen=True)
class QuizQuestion:
    """One multiple-choice check at the end of a lesson."""

    question: str
    options: tuple[str, ...]
    answer_index: int
    explanation: str

    def is_correct(self, choice: int) -> bool:
        return choice == self.answer_index


@dataclass(frozen=True)
class LessonContent:
    """A complete lesson: title, body, optional image, and quiz."""

    number: int
    level: int
    title: str
    body: str
    quiz: QuizQuestion
    image_path: str | None = None


def _q(question: str, options: tuple[str, ...], answer: int, why: str) -> QuizQuestion:
    return QuizQuestion(question, options, answer, why)


# --------------------------------------------------------------------------
# Level 1 — Trading from zero (lessons 1-20)
# --------------------------------------------------------------------------

_LEVEL_1: tuple[LessonContent, ...] = (
    LessonContent(
        1, 1, "What is cryptocurrency?",
        "Cryptocurrency is digital money that lives on a shared record "
        "called a blockchain. Nobody prints it in a basement; computers "
        "all over the world agree on who owns what. It has no government "
        "behind it, which is its freedom and also its danger: if you send "
        "it to the wrong address, no bank can reverse it.",
        _q("What makes cryptocurrency different from a bank balance?",
           ("It is digital and secured by a shared network, with no bank able to reverse a mistake",
            "It is printed by a government", "It is stored in a physical coin"),
           0, "Crypto is peer-to-peer digital money: convenient, but mistakes are usually final."),
    ),
    LessonContent(
        2, 1, "What is a market?",
        "A market is simply a place where buyers and sellers meet and "
        "agree on a price. In crypto the market is a computer program "
        "matching orders all day, every day. Price is not a fact; it is "
        "the last price at which two people agreed.",
        _q("What is a market price?",
           ("The last price at which a buyer and a seller agreed",
            "A value fixed by the exchange", "The average price of the year"),
           0, "Prices are agreements, and they change the moment a new agreement happens."),
    ),
    LessonContent(
        3, 1, "What is a trading pair?",
        "A trading pair like BTC/USDT means “how much USDT does one BTC "
        "cost?”. The first asset is what you buy or sell; the second is "
        "what you pay with. BTC/USDT and USDT/BTC are different markets "
        "moving in opposite directions.",
        _q("In the pair BTC/USDT, what does the price tell you?",
           ("How many USDT one BTC costs", "How many BTC one USDT costs",
            "The total value of all Bitcoin"),
           0, "BASE/QUOTE: the quote asset is the one you pay with."),
    ),
    LessonContent(
        4, 1, "What is a candlestick?",
        "A candlestick packs one period of trading into four prices: "
        "open, high, low and close. The body spans open to close; the "
        "thin wicks show the extremes reached. Green usually means the "
        "close was above the open, red the opposite — colours are "
        "convention, not meaning.",
        _q("What four prices does a candlestick contain?",
           ("Open, high, low, close", "Bid, ask, spread, volume",
            "Buy, sell, fee, profit"),
           0, "OHLC: the four numbers that summarise a period."),
        image_path="assets/tutorial/candlestick_chart.png",
    ),
    LessonContent(
        5, 1, "What is volume?",
        "Volume is how much was traded in the period. A price move on "
        "tiny volume may be noise; the same move on heavy volume means "
        "many people agreed. Volume does not tell you the future, but "
        "it tells you whether a move had participation.",
        _q("Why does volume matter?",
           ("It shows how much participation a price move had",
            "It predicts tomorrow's price", "It is the same as market cap"),
           0, "Price plus volume is more informative than price alone."),
    ),
    LessonContent(
        6, 1, "What is a market order?",
        "A market order says “fill me now, at whatever price is "
        "available”. You get certainty of execution and uncertainty of "
        "price. In thin markets that price can be much worse than the "
        "one you saw a second ago.",
        _q("What do you trade away with a market order?",
           ("Price certainty: you may be filled at a worse price",
            "Nothing, it is always exact", "The ability to sell later"),
           0, "Speed of execution and certainty of price are different things."),
    ),
    LessonContent(
        7, 1, "What is a limit order?",
        "A limit order says “only fill me at this price or better”. You "
        "control the price and accept the risk that it never fills. If "
        "your limit is far from the market, you may wait forever while "
        "the price runs away from you.",
        _q("What is the main risk of a limit order?",
           ("It may never be filled", "It always pays more fees",
            "It executes at any price"),
           0, "Limit orders trade execution certainty for price certainty."),
    ),
    LessonContent(
        8, 1, "What are fees?",
        "Every trade pays the exchange a commission (a taker fee when "
        "you cross the spread, a maker fee when you provide liquidity). "
        "Fees look tiny per trade and are enormous per year: a strategy "
        "that trades often can lose to fees alone, even when it is right "
        "about direction.",
        _q("Why do fees matter so much?",
           ("They are paid on every trade, so frequent trading multiplies them",
            "They are a one-time payment", "They only apply to withdrawals"),
           0, "Costs are one of the most common reasons a backtest does not survive reality."),
    ),
    LessonContent(
        9, 1, "What is risk?",
        "Risk is not volatility; risk is the chance of losing money you "
        "cannot afford to lose. Two traders can hold the same asset and "
        "have completely different risk, because risk depends on how "
        "much of their survival money is exposed.",
        _q("What is the practical definition of risk here?",
           ("The chance of losing money you cannot afford to lose",
            "How fast the price moves", "How famous the coin is"),
           0, "Position size and personal situation determine risk, not the asset alone."),
    ),
    LessonContent(
        10, 1, "What is paper trading?",
        "Paper trading uses real market prices with imaginary money. It "
        "lets you practise order entry, exits and discipline without "
        "risking a cent. It is honest practice, not proof: real money "
        "brings fear and slippage that paper fills do not reproduce.",
        _q("What does paper trading fail to reproduce?",
           ("The emotions and the real execution costs of live money",
            "Market prices", "Order types"),
           0, "Use paper trading to build habits, not to conclude that you will profit."),
        image_path="assets/tutorial/paper_trading.png",
    ),
    LessonContent(
        11, 1, "What is backtesting?",
        "Backtesting runs a fixed rule over historical candles and "
        "computes what would have happened, costs included. It is a "
        "time machine with a flaw: the market you tested has already "
        "happened, and the future is not a replay of the past.",
        _q("What is a backtest?",
           ("A simulation of fixed rules over historical data",
            "A prediction of next month's price", "A type of exchange order"),
           0, "A backtest is an experiment about the past; it is not a forecast."),
        image_path="assets/tutorial/backtesting.png",
    ),
    LessonContent(
        12, 1, "Build your first simple strategy.",
        "A strategy needs an entry rule, an exit rule and a position "
        "size. Start with something boring you can explain in one "
        "sentence, such as “buy when the fast average rises above the "
        "slow one, sell when it falls back below”. If you cannot explain "
        "it simply, you cannot test it honestly.",
        _q("What are the three parts every strategy needs?",
           ("Entry rule, exit rule and position size",
            "A prediction, a hope and luck", "An indicator, a colour and a hunch"),
           0, "Simple, explainable rules are the only ones you can validate."),
        image_path="assets/tutorial/strategy_builder.png",
    ),
    LessonContent(
        13, 1, "Run your first backtest.",
        "In this laboratory you download a dataset, open the Backtesting "
        "Lab, choose a strategy and press Run. Then read the warnings "
        "before the numbers: costs, sample size, and whether the result "
        "beat simply holding the asset.",
        _q("What should you do first with a backtest result?",
           ("Read its assumptions and warnings, then compare with buy and hold",
            "Assume it will repeat", "Increase the position size"),
           0, "A result without its assumptions is marketing, not research."),
    ),
    LessonContent(
        14, 1, "Understand a loss.",
        "Losses are a normal cost of doing business, like fuel for a "
        "truck. What destroys traders is not a losing trade; it is a "
        "losing trade that was too big, or a loss that was denied and "
        "held until it became catastrophic. Decide your exit before you "
        "enter, and obey it.",
        _q("What actually destroys trading accounts?",
           ("Losses that are too large, or denied until they become huge",
            "Any loss at all", "Small losses taken quickly"),
           0, "The size of a loss matters far more than the fact of losing."),
    ),
    LessonContent(
        15, 1, "Understand drawdown.",
        "Drawdown is the fall from a previous peak of your account. A "
        "50% drawdown needs a 100% gain just to get back to even. This "
        "asymmetry is why professionals obsess over drawdown, and why "
        "“how much can I lose?” comes before “how much can I make?”.",
        _q("After a 50% drawdown, how much gain returns you to the previous peak?",
           ("100%", "50%", "25%"),
           0, "Losses compound against you: protecting capital is not optional."),
    ),
    LessonContent(
        16, 1, "Learn why profits are never guaranteed.",
        "No program, indicator or expert can promise that the future "
        "will resemble the past. Markets are made of people, and people "
        "change. This laboratory tries to find and validate a real edge, "
        "and it will tell you honestly when it cannot find one.",
        _q("What can this laboratory honestly promise?",
           ("Honest measurement and a clear “no edge found” when that is the truth",
            "Guaranteed monthly profit", "A prediction of the next peak"),
           0, "The honest ambition is a real chance, never a promise."),
    ),
    LessonContent(
        17, 1, "Why most traders lose money.",
        "Most losses come from costs, oversized positions, overtrading, "
        "and strategies selected because they looked great in the past. "
        "Each of those is a measurable mistake, which means each can be "
        "fixed with discipline and evidence.",
        _q("Which is a common, measurable cause of trader losses?",
           ("Overtrading and oversized positions", "Reading too many books",
            "Using a computer"),
           0, "If a mistake is measurable, it can be corrected."),
    ),
    LessonContent(
        18, 1, "Trading is not a reliable income.",
        "Trading income arrives in irregular bursts and can vanish for "
        "months. Anyone who needs a predictable monthly salary should "
        "not depend on markets for it. Treat trading as a research "
        "project that may, one day, pay — never as a wage.",
        _q("Why is trading a poor substitute for a salary?",
           ("Its income is irregular and can disappear for long periods",
            "It is illegal", "It requires no skill"),
           0, "Never build your survival budget on trading income."),
    ),
    LessonContent(
        19, 1, "When not to trade.",
        "Do not trade when you are emotional, when you need the money, "
        "when the market is thinner than your order, when your system is "
        "down, or when you are testing an unvalidated idea with real "
        "money. Not trading is a decision, and often the profitable one.",
        _q("Which is a good reason NOT to trade?",
           ("You need the money for living expenses", "The chart is green",
            "You have free time"),
           0, "The best trade is sometimes no trade."),
    ),
    LessonContent(
        20, 1, "Protecting the money you need for living.",
        "Capital protection comes before profit seeking. Keep an "
        "emergency fund outside the exchange, never borrow to trade, and "
        "never expose rent or food money. A trader who survives can "
        "learn; a trader who is wiped out cannot.",
        _q("What comes first, always?",
           ("Protecting the money you need to live", "Maximising returns",
            "Beating the market this month"),
           0, "Survive → validate → earn. In that order, non-negotiable."),
    ),
)


# --------------------------------------------------------------------------
# Level 2 — Practical trading (lessons 21-36)
# --------------------------------------------------------------------------

_LEVEL_2: tuple[LessonContent, ...] = (
    LessonContent(
        21, 2, "Support and resistance",
        "Support is a price area where buyers have repeatedly appeared; "
        "resistance is where sellers have. They are zones, not exact "
        "lines, and they are descriptive: they record where the market "
        "previously disagreed about value.",
        _q("What is support?",
           ("A price zone where buyers repeatedly appeared",
            "A guarantee the price will stop falling", "A type of order"),
           0, "Levels are areas of past agreement, not promises about the future."),
    ),
    LessonContent(
        22, 2, "Trend",
        "An uptrend makes higher highs and higher lows; a downtrend makes "
        "lower highs and lower lows. Trend-following strategies try to "
        "join moves already in progress and accept many small losses "
        "while waiting for the big one.",
        _q("What defines an uptrend?",
           ("Higher highs and higher lows", "A green candle",
            "Volume above average"),
           0, "Trend is a sequence of structure, not a single candle."),
    ),
    LessonContent(
        23, 2, "Range",
        "A range is a market with no clear direction, bouncing between "
        "two levels. Trend strategies bleed in ranges while mean-"
        "reversion strategies bleed in trends; knowing which regime you "
        "are in matters more than the indicator you choose.",
        _q("Which strategy type usually suffers in a range?",
           ("Trend following", "Mean reversion", "Buy and hold forever"),
           0, "Every strategy has a regime where it fails. Know yours."),
    ),
    LessonContent(
        24, 2, "Volatility",
        "Volatility measures how much price moves, not which direction. "
        "High volatility means bigger opportunities and bigger losses, "
        "so position size must shrink when volatility rises.",
        _q("What does volatility measure?",
           ("The size of price movement, regardless of direction",
            "The direction of the trend", "The exchange's fee"),
           0, "Volatility is the size of the waves, not their direction."),
    ),
    LessonContent(
        25, 2, "ATR",
        "Average True Range averages the true range of recent candles, "
        "including gaps. Traders use it to set stops that breathe: a "
        "stop closer than one ATR is likely to be hit by ordinary noise.",
        _q("What is ATR useful for?",
           ("Sizing stops to the market's normal movement",
            "Predicting the close", "Measuring fees"),
           0, "A stop smaller than normal noise is not a stop, it is a donation."),
        image_path="assets/tutorial/chart_with_indicators.png",
    ),
    LessonContent(
        26, 2, "Momentum",
        "Momentum measures the speed of a move, often with RSI or ROC. "
        "Strong momentum can persist, but it can also mean the move is "
        "exhausted. Momentum is evidence about the recent past, never a "
        "promise about the next candle.",
        _q("What does momentum describe?",
           ("The speed and strength of a recent move",
            "The long-term average price", "The number of traders online"),
           0, "Momentum is about the recent past, not the future."),
    ),
    LessonContent(
        27, 2, "Mean reversion",
        "Mean reversion assumes that stretched prices tend to return to "
        "an average. It works often and loses badly when a real trend "
        "starts, so risk control matters more here than in any other "
        "family.",
        _q("What is the main danger of mean reversion?",
           ("A strong trend that never returns to the average",
            "Paying too little in fees", "Using a chart"),
           0, "Mean reversion wins small and loses big unless it is risk-controlled."),
    ),
    LessonContent(
        28, 2, "Breakout",
        "A breakout is a move beyond a level that had been holding. "
        "Breakouts attract attention and often fail (false breakouts), "
        "which is why volume and a defined invalidation point matter.",
        _q("What is a false breakout?",
           ("A move beyond a level that quickly reverses back",
            "A breakout on high volume", "A limit order"),
           0, "Breakouts need a plan for being wrong."),
    ),
    LessonContent(
        29, 2, "Volume",
        "Volume confirms participation. Rising price on falling volume "
        "is a warning; a breakout on strong volume is more credible than "
        "one on thin trading. In crypto, beware wash trading on small "
        "exchanges.",
        _q("What does falling volume during a rally suggest?",
           ("The move has weaker participation", "The move is guaranteed",
            "Fees will fall"),
           0, "Participation is evidence; its absence is a warning."),
    ),
    LessonContent(
        30, 2, "Liquidity",
        "Liquidity is how much you can trade without moving the price. "
        "A market can show a great price on screen and still be "
        "untradeable in size. Your strategy must match the liquidity of "
        "the market you actually trade.",
        _q("What is liquidity?",
           ("The ability to trade size without moving the price much",
            "The number of coins that exist", "The exchange's uptime"),
           0, "A price you cannot trade in your size is not your price."),
    ),
    LessonContent(
        31, 2, "Spread",
        "The spread is the gap between the best bid and the best ask. "
        "You pay it on every round trip, so it is a real cost the moment "
        "you use market orders. Wide spreads are a hidden tax on active "
        "trading.",
        _q("When do you pay the spread?",
           ("On every round trip, especially with market orders",
            "Only on withdrawals", "Never on crypto exchanges"),
           0, "The spread is a cost, not a detail."),
    ),
    LessonContent(
        32, 2, "Slippage",
        "Slippage is the difference between the price you expected and "
        "the price you got. It grows with order size, volatility and "
        "thin books. Backtests that assume perfect fills flatter fast "
        "strategies.",
        _q("What causes slippage?",
           ("Order size, volatility and thin order books",
            "Using limit orders", "Holding too long"),
           0, "Real fills are worse than ideal fills, especially when it matters."),
    ),
    LessonContent(
        33, 2, "Position sizing",
        "Position sizing decides how much you risk per trade, and it "
        "matters more than entry timing. Risking a fixed small fraction "
        "of capital keeps a losing streak survivable; risking a fixed "
        "large amount eventually ends the account.",
        _q("What determines how long you survive a losing streak?",
           ("How much you risk per trade", "How many indicators you use",
            "How often you check the chart"),
           0, "Survival is a position-sizing problem before it is a prediction problem."),
    ),
    LessonContent(
        34, 2, "Expectancy",
        "Expectancy is the average result per trade: (win rate × average "
        "win) − (loss rate × average loss). A strategy can win 30% of the "
        "time and still be profitable, or win 90% and lose money.",
        _q("Can a strategy with a 30% win rate make money?",
           ("Yes, if the average win is much larger than the average loss",
            "No, never", "Only with leverage"),
           0, "Expectancy, not win rate, decides profitability."),
    ),
    LessonContent(
        35, 2, "R-multiple",
        "Express every result in units of the risk you took (R). A trade "
        "that risks 100 to make 300 is +3R regardless of account size. "
        "Thinking in R makes results comparable across markets and "
        "periods.",
        _q("If you risk 50 and make 150, what is the result in R?",
           ("+3R", "+1R", "+150R"),
           0, "R normalises results by the risk taken."),
    ),
    LessonContent(
        36, 2, "Risk of ruin",
        "Risk of ruin is the probability that a losing streak destroys "
        "your account. It depends on your edge, your bet size and your "
        "number of bets. Even a positive-expectancy strategy can ruin "
        "you if each bet is too large.",
        _q("What most increases the risk of ruin?",
           ("Betting too large a fraction per trade",
            "Trading a liquid market", "Keeping a journal"),
           0, "Size, not edge alone, decides whether you survive."),
    ),
)


# --------------------------------------------------------------------------
# Level 3 — Quantitative research (lessons 37-48)
# --------------------------------------------------------------------------

_LEVEL_3: tuple[LessonContent, ...] = (
    LessonContent(
        37, 3, "Hypothesis",
        "A research hypothesis is a falsifiable sentence: “when price is "
        "above EMA200 and RSI crosses 50 upward, BTC/USDT 1h continues "
        "higher over the next 24 hours”. If no observation could prove it "
        "wrong, it is not a hypothesis.",
        _q("What makes a hypothesis scientific?",
           ("It could be proven wrong by data", "It sounds confident",
            "It uses several indicators"),
           0, "A claim that cannot fail cannot teach you anything."),
    ),
    LessonContent(
        38, 3, "Variables",
        "Define what you measure (the return after a signal), what you "
        "vary (parameters), and what you hold fixed (costs, period, "
        "market). Undefined variables are how accidental cheating enters "
        "research.",
        _q("Why define variables explicitly?",
           ("So the experiment is reproducible and free of accidental cheating",
            "To make the code shorter", "Because exchanges require it"),
           0, "Ambiguity in research becomes bias in results."),
    ),
    LessonContent(
        39, 3, "Train and test",
        "Split history chronologically: develop on the training part and "
        "check on a part the strategy has never seen. Shuffling time "
        "series leaks the future into the past and manufactures fake "
        "edges.",
        _q("How should financial data be split?",
           ("Chronologically, never shuffled", "Randomly, for balance",
            "By asset"),
           0, "Time has an order, and the test set must come last."),
    ),
    LessonContent(
        40, 3, "Out-of-sample",
        "The out-of-sample period is the final exam. If you look at it "
        "repeatedly while adjusting your strategy, it stops being an "
        "exam and becomes training data. Budget how many times you will "
        "use it.",
        _q("What happens if you reuse the test set many times?",
           ("It slowly becomes training data and stops being evidence",
            "It becomes more reliable", "Nothing changes"),
           0, "Every peek at the test set spends a little of its value."),
    ),
    LessonContent(
        41, 3, "Walk-forward",
        "Walk-forward analysis rolls the window: train, test forward, "
        "move forward, repeat. It mimics how you would have traded in "
        "real time and shows whether the strategy survives changing "
        "conditions.",
        _q("What does walk-forward analysis simulate?",
           ("Repeatedly training and testing forward in time",
            "A single backtest on all data", "Buying and holding"),
           0, "Walk-forward is closer to reality than one big backtest."),
    ),
    LessonContent(
        42, 3, "Overfitting",
        "Overfitting is fitting the noise of the past. Its symptoms: "
        "many parameters, spectacular backtests, and collapse on new "
        "data. The cure is fewer parameters, more data, and genuine "
        "out-of-sample testing.",
        _q("Which is a symptom of overfitting?",
           ("Excellent backtest results that collapse out of sample",
            "Few parameters", "A clear hypothesis"),
           0, "If it only works on the data you tuned it on, it works on nothing."),
    ),
    LessonContent(
        43, 3, "Multiple testing",
        "If you try 200 configurations, the best one will look great by "
        "luck alone. Always record how many things you tried, and treat "
        "the winner as the best of many guesses until it survives an "
        "independent test.",
        _q("Why does testing many configurations inflate results?",
           ("The best of many random tries looks skilled by chance",
            "It costs more fees", "It uses too much memory"),
           0, "Selection bias is the most common way research lies to itself."),
    ),
    LessonContent(
        44, 3, "Monte Carlo",
        "Monte Carlo resamples your own trades into thousands of "
        "alternative sequences. It answers “how bad could this have "
        "been?” by showing the distribution of outcomes, including the "
        "risk of ruin.",
        _q("What does trade-resampling Monte Carlo show?",
           ("The distribution of outcomes and the risk of ruin",
            "The exact future return", "The best parameter values"),
           0, "Monte Carlo explores the range of plausible histories, not the future."),
    ),
    LessonContent(
        45, 3, "Bootstrap",
        "The bootstrap estimates uncertainty by resampling your data "
        "with replacement. It gives confidence intervals for statistics "
        "like the mean return, which is far more honest than a single "
        "point estimate.",
        _q("What does a bootstrap provide?",
           ("A confidence interval for a statistic",
            "A guarantee of profit", "A new strategy"),
           0, "Uncertainty stated honestly is more useful than false precision."),
    ),
    LessonContent(
        46, 3, "Regimes",
        "Markets alternate between regimes: trending, ranging, calm, "
        "turbulent. A strategy's edge often exists in one regime only. "
        "Analysing by regime tells you when your edge is likely to be "
        "present.",
        _q("Why analyse performance by regime?",
           ("A strategy's edge often exists only in some market conditions",
            "To increase the number of trades", "To avoid paying fees"),
           0, "Knowing when an edge works is as important as knowing that it does."),
    ),
    LessonContent(
        47, 3, "Robustness",
        "A robust strategy still behaves sensibly when parameters, costs "
        "and periods change slightly. If a 1-period change in a moving "
        "average destroys the result, you found noise, not an edge.",
        _q("What does robustness mean?",
           ("The result survives small changes in assumptions",
            "The result is extremely high", "The strategy trades often"),
           0, "Fragile results are usually artifacts."),
    ),
    LessonContent(
        48, 3, "Statistical significance",
        "With few observations, almost any result can happen by chance. "
        "Report sample size, be sceptical of ratios from small samples, "
        "and remember that a p-value is not a promise of profit.",
        _q("What must accompany a performance statistic?",
           ("The sample size and its uncertainty",
            "A confident tone", "A screenshot"),
           0, "A number without its uncertainty is not evidence."),
    ),
)


CURRICULUM: tuple[LessonContent, ...] = _LEVEL_1 + _LEVEL_2 + _LEVEL_3


def lessons_for_level(level: int) -> tuple[LessonContent, ...]:
    """All lessons in a level, in order."""
    return tuple(lesson for lesson in CURRICULUM if lesson.level == level)


def get_lesson(number: int) -> LessonContent | None:
    """Fetch one lesson by its global number."""
    for lesson in CURRICULUM:
        if lesson.number == number:
            return lesson
    return None


def total_lessons() -> int:
    """Total lessons across every level."""
    return len(CURRICULUM)
