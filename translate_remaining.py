#!/usr/bin/env python3
"""Add remaining Spanish translations"""

import xml.etree.ElementTree as ET

ts_path = "/home/wachin/Dev3/crypto-trading-lab/src/crypto_trading_lab/i18n/translations/crypto_trading_lab_es.ts"

tree = ET.parse(ts_path)
root = tree.getroot()

translations = {
    "Disconnected": "Desconectado",
    "Open the {screen} from the main menu to try it.": "Abra {screen} desde el menú principal para probarlo.",
    "Exit: {exit_time} at {exit_price}\nP/L: {pnl}": "Salida: {exit_time} a {exit_price}\nP/L: {pnl}",
    "Parameter sweep…": "Barrido de parámetros…",
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
print("Remaining translations updated!")