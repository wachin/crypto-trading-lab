#!/usr/bin/env python3
"""Add final Spanish translations"""

import xml.etree.ElementTree as ET

ts_path = "/home/wachin/Dev3/crypto-trading-lab/src/crypto_trading_lab/i18n/translations/crypto_trading_lab_es.ts"

tree = ET.parse(ts_path)
root = tree.getroot()

translations = {
    "Lesson {number} relates to {screen}.\n\nOpen the {screen} from the main menu to try it.": "La lección {number} se relaciona con {screen}.\n\nAbra {screen} desde el menú principal para probarlo.",
    "Trade #{number} — {signal}\nDecision time: {time}\nReference price: {ref}\nRisk decision: {risk} — {reason}\nFill: {fill_time} at {fill_price}\nExit: {exit_time} at {exit_price}\nP/L: {pnl}": "Operación #{number} — {signal}\nHora de decisión: {time}\nPrecio de referencia: {ref}\nDecisión de riesgo: {risk} — {reason}\nLlenado: {fill_time} a {fill_price}\nSalida: {exit_time} a {exit_price}\nP/L: {pnl}",
}

for msg in root.findall(".//message"):
    source = msg.find("source")
    translation = msg.find("translation")
    if source is not None and translation is not None:
        source_text = source.text
        if source_text in translations:
            translation.text = translations[source_text]
            translation.set("type", "translated")

tree.write(ts_path, encoding="utf-8", xml_declaration=True)
print("Final translations updated!")