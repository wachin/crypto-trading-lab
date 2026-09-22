"""
Generate tutorial images for Crypto Trading Lab Learning Center.

Creates both SVG (editable in Inkscape) and PNG (runtime) versions.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import xml.etree.ElementTree as ET

ASSETS_DIR = Path("/home/wachin/Dev3/crypto-trading-lab/src/crypto_trading_lab/education/assets/tutorial")
ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def _save_svg(svg_root, name):
    """Write SVG file."""
    tree = ET.ElementTree(svg_root)
    tree.write(ASSETS_DIR / f'{name}.svg', encoding='utf-8', xml_declaration=True)
    print(f"  ✓ {name}.svg")


def _save_png(fig, name):
    """Write PNG file."""
    fig.savefig(ASSETS_DIR / f'{name}.png', dpi=150, facecolor='#f8f9fa')
    plt.close(fig)
    print(f"  ✓ {name}.png")


# ── 1. Candlestick chart ────────────────────────────────────────────
def candlestick(name="candlestick_chart"):
    np.random.seed(42)
    n = 20
    opens = 100 + np.cumsum(np.random.randn(n) * 2)
    closes = opens + np.random.randn(n) * 3
    highs = np.maximum(opens, closes) + np.abs(np.random.randn(n) * 2)
    lows = np.minimum(opens, closes) - np.abs(np.random.randn(n) * 2)

    # SVG
    svg = ET.Element('svg', xmlns='http://www.w3.org/2000/svg',
                     width='600', height='300', viewBox='0 0 600 300')
    ET.SubElement(svg, 'rect', x='0', y='0', width='600', height='300', fill='#f8f9fa')
    ET.SubElement(svg, 'text', x='300', y='30',
                  **{'text-anchor': 'middle', 'font-size': '16',
                     'font-weight': 'bold', 'fill': '#333'}).text = 'Candlestick Chart'
    for i in range(n):
        x = 30 + i * 28
        color = '#2e7d32' if closes[i] > opens[i] else '#c62828'
        ET.SubElement(svg, 'line', x1=str(x), y1=str(lows[i]),
                      x2=str(x), y2=str(highs[i]),
                      stroke=color, **{'stroke-width': '2'})
        top = min(opens[i], closes[i])
        h = max(3, abs(opens[i] - closes[i]))
        ET.SubElement(svg, 'rect', x=str(x-10), y=str(top),
                      width='20', height=str(h), fill=color, stroke=color)
    _save_svg(svg, name)

    # PNG
    fig, ax = plt.subplots(figsize=(10, 5), facecolor='#f8f9fa')
    colors = ['#2e7d32' if c > o else '#c62828' for o, c in zip(opens, closes)]
    for i in range(n):
        ax.plot([i, i], [lows[i], highs[i]], color=colors[i], linewidth=1.5)
        ax.bar(i, abs(opens[i] - closes[i]), bottom=min(opens[i], closes[i]),
               width=0.6, color=colors[i], edgecolor=colors[i])
    ax.set_title('Candlestick Chart', fontsize=14, fontweight='bold')
    ax.set_xlabel('Time'); ax.set_ylabel('Price'); ax.grid(True, alpha=0.3)
    plt.tight_layout()
    _save_png(fig, name)


# ── 2. Chart with indicators ────────────────────────────────────────
def indicators(name="chart_with_indicators"):
    np.random.seed(123)
    x = np.arange(50)
    price = 100 + np.cumsum(np.random.randn(50) * 0.5)
    sma20 = np.convolve(price, np.ones(20)/20, mode='same')
    sma50 = np.convolve(price, np.ones(50)/50, mode='same')

    # SVG
    svg = ET.Element('svg', xmlns='http://www.w3.org/2000/svg',
                     width='600', height='300', viewBox='0 0 600 300')
    ET.SubElement(svg, 'rect', x='0', y='0', width='600', height='300', fill='#f8f9fa')
    ET.SubElement(svg, 'text', x='300', y='30',
                  **{'text-anchor': 'middle', 'font-size': '16',
                     'font-weight': 'bold', 'fill': '#333'}).text = 'Chart with Indicators'
    # Price line
    pts = [(30 + i*10, 270 - p*1.5) for i, p in enumerate(price)]
    for i in range(len(pts)-1):
        ET.SubElement(svg, 'line', x1=str(pts[i][0]), y1=str(pts[i][1]),
                      x2=str(pts[i+1][0]), y2=str(pts[i+1][1]),
                      stroke='#1976d2', **{'stroke-width': '2'})
    # SMA20
    s20 = [(30 + i*10, 270 - p*1.5) for i, p in enumerate(sma20)]
    for i in range(len(s20)-1):
        ET.SubElement(svg, 'line', x1=str(s20[i][0]), y1=str(s20[i][1]),
                      x2=str(s20[i+1][0]), y2=str(s20[i+1][1]),
                      stroke='#f57c00', **{'stroke-width': '2', 'stroke-dasharray': '5,5'})
    # SMA50
    s50 = [(30 + i*10, 270 - p*1.5) for i, p in enumerate(sma50)]
    for i in range(len(s50)-1):
        ET.SubElement(svg, 'line', x1=str(s50[i][0]), y1=str(s50[i][1]),
                      x2=str(s50[i+1][0]), y2=str(s50[i+1][1]),
                      stroke='#c62828', **{'stroke-width': '2', 'stroke-dasharray': '5,5'})
    # Legend
    ET.SubElement(svg, 'text', x='10', y='20', font_size='12', fill='#1976d2').text = 'Price'
    ET.SubElement(svg, 'text', x='10', y='40', font_size='12', fill='#f57c00').text = 'SMA (20)'
    ET.SubElement(svg, 'text', x='10', y='60', font_size='12', fill='#c62828').text = 'SMA (50)'
    _save_svg(svg, name)

    # PNG
    fig, ax = plt.subplots(figsize=(10, 5), facecolor='#f8f9fa')
    ax.plot(price, label='Price', color='#1976d2', linewidth=1.5)
    ax.plot(sma20, label='SMA (20)', color='#f57c00', linewidth=1.5, linestyle='--')
    ax.plot(sma50, label='SMA (50)', color='#c62828', linewidth=1.5, linestyle=':')
    ax.set_title('Chart with Technical Indicators', fontsize=14, fontweight='bold')
    ax.set_xlabel('Time'); ax.set_ylabel('Price')
    ax.legend(); ax.grid(True, alpha=0.3)
    plt.tight_layout()
    _save_png(fig, name)


# ── 3. Strategy builder ─────────────────────────────────────────────
def strategy(name="strategy_builder"):
    # SVG
    svg = ET.Element('svg', xmlns='http://www.w3.org/2000/svg',
                     width='600', height='300', viewBox='0 0 600 300')
    ET.SubElement(svg, 'rect', x='0', y='0', width='600', height='300', fill='#f8f9fa')
    ET.SubElement(svg, 'text', x='200', y='30',
                  **{'text-anchor': 'middle', 'font-size': '18',
                     'font-weight': 'bold', 'fill': '#333'}).text = 'Strategy Builder'
    # Palette
    ET.SubElement(svg, 'rect', x='40', y='60', width='180', height='200',
                  fill='#fff', stroke='#ccc', **{'stroke-width': '1'})
    ET.SubElement(svg, 'text', x='130', y='80',
                  **{'text-anchor': 'middle', 'font-size': '12', 'fill': '#666'}).text = 'Block Palette'
    blocks = ['Indicators', 'Values', 'Crossover', 'Crossunder', 'AND/OR', 'Entry', 'Exit', 'Stop-loss', 'Take-profit']
    for i, b in enumerate(blocks):
        ET.SubElement(svg, 'rect', x='45', y='100+i*20', width='170', height='18',
                      fill='#e8f5e9', stroke='#2e7d32', **{'stroke-width': '1'})
        ET.SubElement(svg, 'text', x='55', y='113+i*20', font_size='10', fill='#333').text = b
    # Canvas
    ET.SubElement(svg, 'rect', x='270', y='60', width='290', height='200',
                  fill='#fff', stroke='#ccc', **{'stroke-width': '1'})
    ET.SubElement(svg, 'text', x='415', y='80',
                  **{'text-anchor': 'middle', 'font-size': '12', 'fill': '#666'}).text = 'Rule Canvas'
    rules = ['Entry: price > SMA(20)', 'Exit: price < SMA(50)', 'Stop-loss: 2%', 'Take-profit: 5%']
    colors = ['#2e7d32', '#c62828', '#f57c00', '#1976d2']
    for i, (r, c) in enumerate(zip(rules, colors)):
        ET.SubElement(svg, 'text', x='280', y='120+i*25', font_size='11', fill=c).text = r
    # Export button
    ET.SubElement(svg, 'rect', x='200', y='280', width='200', height='30', fill='#1976d2', rx='4')
    ET.SubElement(svg, 'text', x='300', y='300',
                  **{'text-anchor': 'middle', 'font-size': '12', 'fill': '#fff'}).text = 'Export Rule JSON'
    _save_svg(svg, name)

    # PNG
    fig, ax = plt.subplots(figsize=(10, 5), facecolor='#f8f9fa')
    ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis('off')
    ax.add_patch(plt.Rectangle((0.5, 1), 3, 7, fill=True, facecolor='#fff', edgecolor='#ccc', linewidth=1))
    ax.text(2, 9.5, 'Block Palette', ha='center', fontsize=14, fontweight='bold')
    for i, b in enumerate(blocks):
        ax.add_patch(plt.Rectangle((0.8, 7.5 - i*0.7), 2.4, 0.5, facecolor='#e8f5e9', edgecolor='#2e7d32'))
        ax.text(2, 7.7 - i*0.7, b, va='center', fontsize=10)
    ax.add_patch(plt.Rectangle((5, 1), 4, 7, fill=True, facecolor='#fff', edgecolor='#ccc', linewidth=1))
    ax.text(7, 9.5, 'Rule Canvas', ha='center', fontsize=14, fontweight='bold')
    for i, r in enumerate(rules):
        ax.text(6, 7.5 - i*1.2, r, fontsize=11, color=colors[i])
    ax.add_patch(plt.Rectangle((3.5, 0.5), 3, 0.5, facecolor='#1976d2', edgecolor='none'))
    ax.text(5, 0.7, 'Export Rule JSON', ha='center', va='center', fontsize=12, color='white', fontweight='bold')
    ax.set_title('Strategy Builder', fontsize=14, fontweight='bold')
    plt.tight_layout()
    _save_png(fig, name)


# ── 4. Paper trading ────────────────────────────────────────────────
def paper(name="paper_trading"):
    # SVG
    svg = ET.Element('svg', xmlns='http://www.w3.org/2000/svg',
                     width='600', height='300', viewBox='0 0 600 300')
    ET.SubElement(svg, 'rect', x='0', y='0', width='600', height='300', fill='#f8f9fa')
    ET.SubElement(svg, 'text', x='300', y='30',
                  **{'text-anchor': 'middle', 'font-size': '18',
                     'font-weight': 'bold', 'fill': '#333'}).text = 'Paper Trading Simulator'
    # Account
    ET.SubElement(svg, 'rect', x='30', y='50', width='180', height='120', fill='#e8f5e9', stroke='#2e7d32', **{'stroke-width': '1'})
    ET.SubElement(svg, 'text', x='40', y='75', font_size='14', fill='#2e7d32').text = 'Account Balance'
    ET.SubElement(svg, 'text', x='40', y='100', font_size='22', font_weight='bold', fill='#2e7d32').text = '$10,234.56'
    ET.SubElement(svg, 'text', x='40', y='130', font_size='14', fill='#2e7d32').text = 'P/L: +$234.56'
    # Positions
    ET.SubElement(svg, 'rect', x='240', y='50', width='330', height='120', fill='#fff3e0', stroke='#f57c00', **{'stroke-width': '1'})
    ET.SubElement(svg, 'text', x='250', y='75', font_size='14', fill='#f57c00').text = 'Open Positions'
    ET.SubElement(svg, 'text', x='250', y='100', font_size='11', fill='#333').text = 'BTC/USDT  Long  0.5 BTC  +$120'
    ET.SubElement(svg, 'text', x='250', y='125', font_size='11', fill='#333').text = 'ETH/USDT  Short  2.0 ETH  -$45'
    # Journal
    ET.SubElement(svg, 'rect', x='30', y='200', width='540', height='80', fill='#fff', stroke='#ccc', **{'stroke-width': '1'})
    ET.SubElement(svg, 'text', x='40', y='225', font_size='14', fill='#666').text = 'Trading Journal'
    for i, e in enumerate(['1. BUY  BTC/USDT  @ 45,000  Qty: 0.1  Fee: $4.50',
                           '2. SELL BTC/USDT  @ 46,200  Qty: 0.1  Fee: $4.62  P/L: +$115.88',
                           '3. BUY  ETH/USDT  @ 2,500  Qty: 2.0  Fee: $5.00']):
        ET.SubElement(svg, 'text', x='40', y='250+i*15', font_size='9', fill='#333').text = e
    ET.SubElement(svg, 'rect', x='200', y='290', width='200', height='30', fill='#1976d2', rx='4')
    ET.SubElement(svg, 'text', x='300', y='310',
                  **{'text-anchor': 'middle', 'font-size': '12', 'fill': '#fff'}).text = 'Save Journal'
    _save_svg(svg, name)

    # PNG
    fig, ax = plt.subplots(figsize=(10, 5), facecolor='#f8f9fa')
    ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis('off')
    ax.add_patch(plt.Rectangle((0.5, 6), 3, 3, facecolor='#e8f5e9', edgecolor='#2e7d32'))
    ax.text(1.5, 9.5, 'Account Balance', ha='center', fontsize=12, color='#2e7d32')
    ax.text(1.5, 8.5, '$10,234.56', ha='center', fontsize=20, fontweight='bold', color='#2e7d32')
    ax.text(1.5, 7.8, 'P/L: +$234.56', ha='center', fontsize=11, color='#2e7d32')
    ax.add_patch(plt.Rectangle((4.5, 6), 4.5, 3, facecolor='#fff3e0', edgecolor='#f57c00'))
    ax.text(6.75, 9.5, 'Open Positions', ha='center', fontsize=12, color='#f57c00')
    for i, t in enumerate(['BTC/USDT  Long  0.5 BTC  +$120', 'ETH/USDT  Short  2.0 ETH  -$45']):
        ax.text(4.7, 8.5 - i*0.8, t, fontsize=10, color='#333')
    ax.add_patch(plt.Rectangle((0.5, 1), 8, 4, facecolor='#fff', edgecolor='#ccc'))
    ax.text(0.7, 4.8, 'Trading Journal', fontsize=12, color='#666')
    for i, e in enumerate(['1. BUY  BTC/USDT  @ 45,000  Qty: 0.1  Fee: $4.50',
                           '2. SELL BTC/USDT  @ 46,200  Qty: 0.1  Fee: $4.62  P/L: +$115.88',
                           '3. BUY  ETH/USDT  @ 2,500  Qty: 2.0  Fee: $5.00']):
        ax.text(0.7, 4.2 - i*0.7, e, fontsize=9, color='#333')
    ax.add_patch(plt.Rectangle((3.5, 0.3), 3, 0.4, facecolor='#1976d2'))
    ax.text(5, 0.45, 'Save Journal', ha='center', va='center', fontsize=11, color='white', fontweight='bold')
    plt.tight_layout()
    _save_png(fig, name)


# ── 5. Backtesting ──────────────────────────────────────────────────
def backtest(name="backtesting"):
    # SVG
    svg = ET.Element('svg', xmlns='http://www.w3.org/2000/svg',
                     width='600', height='300', viewBox='0 0 600 300')
    ET.SubElement(svg, 'rect', x='0', y='0', width='600', height='300', fill='#f8f9fa')
    ET.SubElement(svg, 'text', x='300', y='30',
                  **{'text-anchor': 'middle', 'font-size': '18',
                     'font-weight': 'bold', 'fill': '#333'}).text = 'Backtesting Lab Results'
    # Equity curve area
    ET.SubElement(svg, 'rect', x='30', y='50', width='540', height='150', fill='#fff', stroke='#ccc', **{'stroke-width': '1'})
    eq = [(30+i*5.4, 180 - p*1.5) for i, p in enumerate(
        [0, 2, -1, 5, 3, 8, 6, 12, 10, 15, 18, 14])]
    for i in range(len(eq)-1):
        ET.SubElement(svg, 'line', x1=str(eq[i][0]), y1=str(eq[i][1]),
                      x2=str(eq[i+1][0]), y2=str(eq[i+1][1]),
                      stroke='#1976d2', **{'stroke-width': '2'})
    ET.SubElement(svg, 'text', x='40', y='45', font_size='12', fill='#1976d2').text = 'Equity Curve (+15.2%)'
    # Metrics
    metrics = [('Net Profit', '+$1,520.00'), ('Max Drawdown', '-8.5%'), ('Sharpe Ratio', '1.42'),
               ('Win Rate', '58%'), ('Profit Factor', '1.85'), ('Total Trades', '147')]
    for i, (label, value) in enumerate(metrics):
        y = 220 + (i % 3) * 25
        x = 30 + (i // 3) * 180
        ET.SubElement(svg, 'text', x=str(x), y=str(y), font_size='12', fill='#333').text = f'{label}: {value}'
    ET.SubElement(svg, 'text', x='30', y='280', font_size='11', fill='#c62828',
                  **{'font-weight': 'bold'}).text = '⚠ This is a backtest, not a guarantee of future profits.'
    _save_svg(svg, name)

    # PNG
    fig, ax = plt.subplots(figsize=(10, 5), facecolor='#f8f9fa')
    np.random.seed(42)
    x = np.arange(100)
    returns = np.cumsum(np.random.randn(100) * 0.01)
    equity = 10000 * (1 + returns)
    ax.plot(equity, color='#1976d2', linewidth=2)
    ax.fill_between(range(100), 10000, equity, alpha=0.2, color='#1976d2')
    ax.axhline(y=10000, color='gray', linestyle=':', alpha=0.5)
    ax.set_title('Backtesting Lab Results', fontsize=14, fontweight='bold')
    ax.set_xlabel('Trades'); ax.set_ylabel('Equity ($)')
    ax.grid(True, alpha=0.3)
    metrics_text = ('Net Profit: +$1,520.00\nMax Drawdown: -8.5%\nSharpe Ratio: 1.42\n'
                    'Win Rate: 58%\nProfit Factor: 1.85\nTotal Trades: 147')
    ax.text(0.02, 0.98, metrics_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    ax.text(0.02, 0.02, '⚠ This is a backtest, not a guarantee of future profits.',
            transform=ax.transAxes, fontsize=9, color='#c62828', fontweight='bold')
    plt.tight_layout()
    _save_png(fig, name)


# ── 6. OHLCV data ───────────────────────────────────────────────────
def ohlcv(name="ohlcv_data"):
    # SVG
    svg = ET.Element('svg', xmlns='http://www.w3.org/2000/svg',
                     width='600', height='300', viewBox='0 0 600 300')
    ET.SubElement(svg, 'rect', x='0', y='0', width='600', height='300', fill='#f8f9fa')
    ET.SubElement(svg, 'text', x='300', y='30',
                  **{'text-anchor': 'middle', 'font-size': '18',
                     'font-weight': 'bold', 'fill': '#333'}).text = 'OHLCV Candle Data'
    # Table header
    cols = ['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']
    cw = [120, 60, 60, 60, 60, 100]
    x = 50
    for i, h in enumerate(cols):
        ET.SubElement(svg, 'rect', x=str(x), y='60', width=str(cw[i]), height='30', fill='#1976d2')
        ET.SubElement(svg, 'text', x=str(x+10), y='80', font_size='11', fill='#fff',
                      font_weight='bold').text = h
        x += cw[i]
    # Data rows
    data = [
        ['2024-01-01 00:00', '42,100', '42,500', '41,900', '42,300', '1,234.56'],
        ['2024-01-01 01:00', '42,300', '42,600', '42,100', '42,450', '987.32'],
        ['2024-01-01 02:00', '42,450', '42,600', '42,100', '42,450', '987.32'],
        ['2024-01-01 03:00', '42,450', '42,600', '42,100', '42,450', '987.32'],
        ['2024-01-01 04:00', '42,450', '42,600', '42,100', '42,450', '987.32'],
    ]
    for ri, row in enumerate(data):
        y = 100 + ri * 28
        if ri % 2 == 0:
            ET.SubElement(svg, 'rect', x='50', y=str(y-10), width='500', height='28', fill='#e8eaf6')
        x = 50
        for ci, val in enumerate(row):
            ET.SubElement(svg, 'text', x=str(x+10), y=str(y+10), font_size='10', fill='#333').text = val
            x += cw[ci]
    ET.SubElement(svg, 'text', x='300', y='260',
                  **{'text-anchor': 'middle', 'font-size': '11', 'fill': '#666'}).text = 'Each row = one candle (OHLCV)'
    _save_svg(svg, name)

    # PNG
    fig, ax = plt.subplots(figsize=(10, 5), facecolor='#f8f9fa')
    ax.axis('off')
    ax.set_title('OHLCV Candle Data', fontsize=14, fontweight='bold', pad=20)
    col_labels = ['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']
    table = ax.table(cellText=data, colLabels=col_labels, cellLoc='center', loc='center',
                     colWidths=[0.18, 0.15, 0.15, 0.15, 0.15, 0.15])
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 2)
    for i in range(len(data) + 1):
        for j in range(6):
            cell = table[i, j]
            if i == 0:
                cell.set_facecolor('#1976d2')
                cell.set_text_props(weight='bold', color='white')
            elif i % 2 == 0:
                cell.set_facecolor('#e8eaf6')
            else:
                cell.set_facecolor('white')
    ax.text(0.5, 0.05, 'Each row = one candle (OHLCV)', ha='center', fontsize=11, color='#666',
            transform=plt.gca().transAxes)
    plt.tight_layout()
    _save_png(fig, name)


if __name__ == '__main__':
    print("=" * 60)
    print("Generating tutorial images (SVG + PNG)...")
    print("=" * 60)
    print("\nImages:")
    candlestick()
    indicators()
    strategy()
    paper()
    backtest()
    ohlcv()
    print("\n" + "=" * 60)
    print("All images generated successfully!")
    print(f"Files saved to: {ASSETS_DIR}")