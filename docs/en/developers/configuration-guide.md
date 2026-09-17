# Configuration Guide (Chapter 71)

## XDG Directories

This application follows the XDG Base Directory Specification.

### Configuration directory

Location: `~/.config/crypto-trading-lab/`

Files:
* `config.json` - User settings
* `credentials.json` - Reference to credential store (actual secrets in system keyring)

### Data directory

Location: `~/.local/share/crypto-trading-lab/`

Files:
* `database.sqlite` - Historical market data
* `experiments/` - Saved experiment results

### Cache directory

Location: `~/.cache/crypto-trading-lab/`

Files:
* `cache.sqlite` - Temporary cached data

## Configuration file structure

```json
{
  "version": "1.0.0",
  "language": "en",
  "theme": "dark",
  "data": {
    "base_url": "https://example.com",
    "default_symbol": "BTC/USDT",
    "default_interval": "1d"
  },
  "backtesting": {
    "initial_capital": 10000,
    "default_fee": 0.001,
    "default_slippage": 0.0005
  },
  "risk": {
    "max_position_percent": 10,
    "max_daily_loss_percent": 5,
    "kill_switch_enabled": true
  }
}
```

## Environment variables

* `CRYPTO_TRADING_LAB_CONFIG` - Override config directory
* `CRYPTO_TRADING_LAB_DATA` - Override data directory
* `QT_QPA_PLATFORM` - Qt platform (offscreen for CI/testing)

## Programmatic access

```python
from crypto_trading_lab.configuration.xdg import ConfigManager

config = ConfigManager()
print(config.data_directory)
print(config.config_file)
```

## Security

* Never store raw API keys in `config.json`
* Use the system keyring for credentials
* Backup configuration regularly
