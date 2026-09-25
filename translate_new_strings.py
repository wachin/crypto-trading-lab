#!/usr/bin/env python3
"""Add Spanish translations for new strings in crypto_trading_lab_es.ts"""

import xml.etree.ElementTree as ET

ts_path = "/home/wachin/Dev3/crypto-trading-lab/src/crypto_trading_lab/i18n/translations/crypto_trading_lab_es.ts"

# Register namespaces
ET.register_namespace('', 'http://www.w3.org/2000/svg')

tree = ET.parse(ts_path)
root = tree.getroot()

# Find all unfinished translations
translations = {
    "No custom rule loaded for sweep.": "No hay ninguna regla personalizada cargada para el barrido.",
    "No sweepable parameters found in this rule. Add a stop-loss, take-profit, or indicators with periods.": "No se encontraron parámetros ajustables en esta regla. Añada un stop-loss, take-profit o indicadores con períodos.",
    "== Parameter sweep: {name} (chapter 39, 77) ==": "== Barrido de parámetros: {name} (capítulo 39, 77) ==",
    "Connection Health": "Salud de la conexión",
    "Not connected to the exchange. No market data is arriving.": "No conectado al intercambio. No llegan datos de mercado.",
    "Help & Troubleshooting": "Ayuda y solución de problemas",
    "See documentation:": "Ver documentación:",
    "Course level": "Nivel del curso",
    "Select the difficulty level of the lessons": "Seleccione el nivel de dificultad de las lecciones",
    "Filter lessons by difficulty level": "Filtrar lecciones por nivel de dificultad",
    "Resume course": "Continuar curso",
    "Jump to the last lesson you were reading": "Ir a la última lección que estaba leyendo",
    "Resume from where you left off": "Continuar desde donde lo dejó",
    "Lesson list": "Lista de lecciones",
    "List of available lessons for the selected level": "Lista de lecciones disponibles para el nivel seleccionado",
    "Lesson content": "Contenido de la lección",
    "Detailed text and images for the selected lesson": "Texto e imágenes detallados de la lección seleccionada",
    "Answer option {n}": "Opción de respuesta {n}",
    "Submit quiz": "Enviar cuestionario",
    "Submit your selected answer for grading": "Enviar su respuesta seleccionada para calificación",
    "Quiz feedback": "Retroalimentación del cuestionario",
    "Explanation showing if your answer was correct or incorrect": "Explicación que muestra si su respuesta fue correcta o incorrecta",
    "Open related tool…": "Abrir herramienta relacionada…",
    "Complete lesson": "Completar lección",
    "Mark this lesson as finished to track progress": "Marcar esta lección como terminada para seguir el progreso",
    "Bookmark lesson": "Guardar lección como favorita",
    "Save this lesson to your bookmarks for quick access": "Guardar esta lección en sus favoritos para acceso rápido",
    "Open tool": "Abrir herramienta",
    "Open the application feature related to this lesson": "Abrir la función de la aplicación relacionada con esta lección",
    "Course status": "Estado del curso",
    "Summary of your overall course progress": "Resumen de su progreso general en el curso",
    "Start introductory lesson": "Comenzar lección introductoria",
    "Begin the first lesson of the beginner level": "Comenzar la primera lección del nivel principiante",
    "Open {screen} for this lesson": "Abrir {screen} para esta lección",
    "Open the {screen} from the main menu to try it.": "Abra {screen} desde el menú principal para probarlo.",
    "REAL TRADING": "TRADING REAL",
    "Application title": "Título de la aplicación",
    "Crypto Trading Lab - Main application window title": "Crypto Trading Lab - Título de la ventana principal de la aplicación",
    "Trading mode indicator": "Indicador de modo de trading",
    "Shows current trading mode: Paper Trading": "Muestra el modo de trading actual: Paper Trading",
    "Real trading status": "Estado del trading real",
    "Shows whether real trading is active or disabled": "Muestra si el trading real está activo o deshabilitado",
    "Real trading warning": "Advertencia de trading real",
    "Visible warning when real trading is active": "Advertencia visible cuando el trading real está activo",
    "Connection status": "Estado de la conexión",
    "Shows current connection state to market data source": "Muestra el estado actual de la conexión con la fuente de datos de mercado",
    "Connection health monitor": "Monitor de salud de la conexión",
    "Detailed connection quality metrics and diagnostics": "Métricas detalladas de calidad de conexión y diagnósticos",
    "Risk warning": "Advertencia de riesgo",
    "Educational message about trading risks and capital protection": "Mensaje educativo sobre riesgos de trading y protección del capital",
    "Welcome message": "Mensaje de bienvenida",
    "Guidance for new users to start with the Learning Center": "Guía para nuevos usuarios para empezar con el Centro de Aprendizaje",
    "Download market data from exchanges": "Descargar datos de mercado de los intercambios",
    "Download real market data from supported exchanges for research": "Descargar datos reales de mercado de los intercambios soportados para investigación",
    "Import CSV market data": "Importar datos de mercado CSV",
    "Load market data from a local CSV file": "Cargar datos de mercado desde un archivo CSV local",
    "Open price chart": "Abrir gráfico de precios",
    "View interactive price charts with indicators": "Ver gráficos de precios interactivos con indicadores",
    "Start interactive trading lessons": "Comenzar lecciones interactivas de trading",
    "Open structured lessons with quizzes and progress tracking": "Abrir lecciones estructuradas con cuestionarios y seguimiento de progreso",
    "Run strategy backtests": "Ejecutar backtests de estrategias",
    "Test trading strategies against historical data with costs": "Probar estrategias de trading contra datos históricos con costes",
    "Start guided research workflow": "Iniciar flujo de trabajo de investigación guiado",
    "Launch the research wizard for hypothesis-driven exploration": "Lanzar el asistente de investigación para exploración basada en hipótesis",
    "Simulated trading with real market data": "Trading simulado con datos de mercado reales",
    "Practice trading with simulated money on real historical data": "Practicar trading con dinero simulado en datos históricos reales",
    "Post-Trade Follow-Up": "Seguimiento Post-Operación",
    "Select a closed trade to see what the strategy knew at the time.": "Seleccione una operación cerrada para ver qué sabía la estrategia en ese momento.",
    "Add a follow-up note for this trade…": "Añadir una nota de seguimiento para esta operación…",
    "Save follow-up note": "Guardar nota de seguimiento",
    "Entry: {entry_time} at {entry_price}\nExit: {exit_time} at {exit_price}\nP/L: {pnl}": "Entrada: {entry_time} a {entry_price}\nSalida: {exit_time} a {exit_price}\nP/L: {pnl}",
    "Follow-up note saved for trade #{number}.": "Nota de seguimiento guardada para la operación #{number}.",
    "Trade #{number}: {signal} — P/L {pnl}": "Operación #{number}: {signal} — P/L {pnl}",
    "Parameter sweep": "Barrido de parámetros",
    "A tradable rule needs both an entry and an exit signal.": "Una regla operable necesita tanto una señal de entrada como una de salida.",
    "No Backtesting Lab window is open. Please open the Backtesting Lab first, then try again.": "No hay ninguna ventana del Laboratorio de Backtesting abierta. Por favor abra primero el Laboratorio de Backtesting e inténtelo de nuevo.",
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
print("Translations updated successfully!")