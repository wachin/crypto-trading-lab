# Troubleshooting the live feed (chapter 27)

The connection health panel shows one state at a time. Each section below
matches one state, says what it means, and lists what to check. The anchor
names are used by the application itself, so do not rename the headings.

The rule that outranks every other piece of advice here: **never act on a
signal built from stale data.** If the panel says the feed is degraded, the
numbers on screen are old, and a strategy evaluated on them is guessing.

## Connection disconnected

Nothing is connected and no reconnection is running. This is the normal state
before you start a feed, and the state after you stop one.

- Check that you started the feed (the CLI `paper-live` command, or the
  panel's connect button).
- Check that the machine has a working internet connection.
- Nothing is wrong with your data or your strategy in this state.

## Connection timeout

The application tried to reach the exchange and the attempt took too long.

- Check your internet connection and any VPN or proxy in between.
- Try again in a minute: exchange endpoints occasionally take longer to
  answer during maintenance.
- If you are on a restricted network, the WebSocket port may be blocked.

## Authentication failed

The exchange rejected the API credentials.

- This cannot happen on a public market-data feed: it only applies to
  authenticated streams and order placement.
- Check that the key belongs to the environment you selected (testnet keys
  do not work on production, and the reverse is also true).
- Check that the key has the permission the operation needs.
- Never paste a key into a chat, an issue or a log. The application redacts
  secrets; your habits should too.

## Subscription failed

The connection is up but the exchange refused one of the streams.

- Check the symbol and interval: `BTC/USDT` and `1m` are valid, `BTC` and
  `7s` are not.
- Some symbols exist on testnet and not on production, or the reverse.
- Reconnecting re-sends every subscription, so a transient failure usually
  fixes itself.

## Connected

The socket is open and messages are arriving. This does not mean the data is
useful yet: a feed can be connected and still deliver nothing for the symbol
you asked for.

- If the candle count does not move, check that the symbol and interval are
  the ones you meant.
- A connected feed that delivers no message for longer than the staleness
  threshold is moved to *Degraded data* automatically.

## Degraded data

The connection is alive but the data is late, incomplete or out of order.
This is the state that matters most, because everything still *looks* fine.

- Do not start a new strategy evaluation while this is showing.
- Check your network for packet loss or a sleeping laptop.
- Wait for the panel to return to *Connected*; the application recovers on
  its own when fresh data arrives.
- If it stays degraded, restart the feed. A gap after reconnection is
  reported with its duration so you can decide whether to trust the window.

## Reconnection loop

The application keeps losing the connection and reconnecting. Backoff
doubles the wait between attempts, so the loop gets slower, not faster.

- Check whether the exchange is in maintenance.
- Check whether something on your network drops long-lived connections
  (some corporate proxies do).
- The loop gives up after the configured maximum number of attempts and
  moves to *Connection error* rather than retrying forever.

## Rate limited

The exchange asked us to slow down and the circuit breaker paused requests.

- Wait: the pause ends automatically.
- If it keeps happening, you are polling too hard somewhere else in your
  workflow (a script of your own, a second copy of the application).
- Rate limits exist to keep the service usable for everyone; do not work
  around them by opening more connections.

## Connection error

The connection failed in a way the application could not recover from, and
the circuit breaker is open.

- Read the message shown with the state; it names the failure.
- Fix the cause (credentials, symbol, network) and start the feed again.
- While the breaker is open, attempts are refused immediately instead of
  hammering the exchange.

## Stopped

The feed was closed on purpose — by you, by the kill switch, or because the
session reached its time limit.

- Nothing is wrong. No data is arriving because nothing is connected.
- The journal and the session result are still valid for the candles that
  did arrive; a stopped session is not a failed one.
