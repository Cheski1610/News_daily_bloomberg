"""
Scheduler que ejecuta el resumen de noticias todos los días a las 20:00.
Ejecutar con: python scheduler.py
"""
import schedule
import time
from datetime import datetime
from main import run


def job():
    print(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] Iniciando resumen diario de noticias...")
    try:
        run()
    except Exception as e:
        print(f"Error durante la ejecución: {e}")


# Programar ejecución diaria a las 20:00
schedule.every().day.at("20:00").do(job)

print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Scheduler iniciado. Próxima ejecución a las 20:00.")
print("Presiona Ctrl+C para detener.\n")

while True:
    schedule.run_pending()
    time.sleep(30)
