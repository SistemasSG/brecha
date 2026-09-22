"""Consulta la tasa BCV y el mejor precio de venta de USDT en Binance P2P.

Escribe una fila en datos/brecha.csv y regenera datos/datos.json, que es lo que
lee el panel. Pensado para correr en GitHub Actions, sin estado entre corridas.
"""
import csv
import json
import os
import re
import sys
import urllib3
from datetime import datetime, timedelta, timezone

import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = os.path.dirname(os.path.abspath(__file__))
DIR_DATOS = os.path.join(BASE, 'datos')
RUTA_CSV = os.path.join(DIR_DATOS, 'brecha.csv')
RUTA_JSON = os.path.join(DIR_DATOS, 'datos.json')
CARACAS = timezone(timedelta(hours=-4))
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def tasa_bcv():
    """Portal del BCV; si su certificado o su HTML fallan, una API pública."""
    try:
        r = requests.get('https://www.bcv.org.ve/', timeout=40, verify=False,
                         headers={'User-Agent': UA})
        m = re.search(r'id="dolar".*?<strong[^>]*>\s*([\d.,]+)\s*</strong>', r.text, re.S)
        if m:
            return float(m.group(1).replace('.', '').replace(',', '.')), 'bcv.org.ve'
    except Exception as e:                                    # noqa: BLE001
        print('BCV directo falló: %s' % e, file=sys.stderr)
    try:
        r = requests.get('https://ve.dolarapi.com/v1/dolares/oficial', timeout=30,
                         headers={'User-Agent': UA})
        d = r.json()
        v = d.get('promedio') or d.get('valor')
        if v:
            return float(v), 'dolarapi'
    except Exception as e:                                    # noqa: BLE001
        print('Respaldo BCV falló: %s' % e, file=sys.stderr)
    return None, None


def precio_binance():
    """Mejor precio al VENDER USDT por 100.000 Bs en Mercantil o Provincial."""
    cuerpo = {
        'fiat': 'VES', 'page': 1, 'rows': 20, 'tradeType': 'SELL', 'asset': 'USDT',
        'transAmount': '100000', 'payTypes': ['Mercantil', 'Provincial'],
        'publisherType': None, 'countries': [],
    }
    try:
        r = requests.post(
            'https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search',
            json=cuerpo, timeout=40,
            headers={'User-Agent': UA, 'Content-Type': 'application/json'})
        anuncios = (r.json() or {}).get('data') or []
        if not anuncios:
            print('Binance devolvió 0 anuncios (HTTP %s)' % r.status_code, file=sys.stderr)
            return None, ''
        mejor = max(anuncios, key=lambda a: float(a['adv']['price']))
        bancos = sorted({m.get('identifier', '') for m in mejor['adv'].get('tradeMethods', [])})
        return float(mejor['adv']['price']), '/'.join(b for b in bancos if b)
    except Exception as e:                                    # noqa: BLE001
        print('Binance falló: %s' % e, file=sys.stderr)
        return None, ''


def filas_csv():
    if not os.path.exists(RUTA_CSV):
        return []
    with open(RUTA_CSV, encoding='utf-8-sig', newline='') as f:
        return [f for f in csv.DictReader(f)]


def escribir_json(filas):
    dias = {}
    for fila in filas:
        try:
            d = dias.setdefault(fila['fecha'], {'fecha': fila['fecha'], 'bcv': 0.0, 'lecturas': []})
            d['bcv'] = float(fila['bcv'])
            if not any(l['hora'] == fila['hora'] for l in d['lecturas']):
                d['lecturas'].append({'hora': fila['hora'], 'p2p': float(fila['p2p']),
                                      'banco': fila.get('banco', ''), 'brecha': float(fila['brecha'])})
        except (KeyError, TypeError, ValueError):
            continue
    salida = []
    for k in sorted(dias):
        dias[k]['lecturas'].sort(key=lambda l: l['hora'])
        salida.append(dias[k])
    with open(RUTA_JSON, 'w', encoding='utf-8') as f:
        json.dump({'actualizado': datetime.now(CARACAS).strftime('%Y-%m-%d %H:%M'),
                   'dias': salida[-120:]}, f, ensure_ascii=False)


def main():
    os.makedirs(DIR_DATOS, exist_ok=True)
    previas = filas_csv()
    if previas and '--forzar' not in sys.argv:
        ult = previas[-1]
        try:
            t = datetime.strptime(ult['fecha'] + ' ' + ult['hora'], '%Y-%m-%d %H:%M').replace(tzinfo=CARACAS)
            if (datetime.now(CARACAS) - t).total_seconds() < 20 * 60:
                print('Ya hay una lectura de las %s; no se repite.' % ult['hora'])
                return 0
        except (KeyError, ValueError):
            pass
    bcv, fuente = tasa_bcv()
    p2p, banco = precio_binance()
    if not bcv or not p2p:
        print('Corrida sin datos: bcv=%s p2p=%s' % (bcv, p2p), file=sys.stderr)
        filas = filas_csv()
        if filas:
            escribir_json(filas)
        return 0
    ahora = datetime.now(CARACAS)
    brecha = (p2p - bcv) / bcv * 100
    nueva = {'fecha': ahora.strftime('%Y-%m-%d'), 'hora': ahora.strftime('%H:%M'),
             'bcv': '%.4f' % bcv, 'p2p': '%.4f' % p2p, 'banco': banco,
             'brecha': '%.4f' % brecha}
    existe = os.path.exists(RUTA_CSV)
    with open(RUTA_CSV, 'a', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['fecha', 'hora', 'bcv', 'p2p', 'banco', 'brecha'])
        if not existe:
            w.writeheader()
        w.writerow(nueva)
    escribir_json(filas_csv())
    print('OK %s %s  bcv=%.4f (%s)  p2p=%.4f  brecha=%.2f%%  %s'
          % (nueva['fecha'], nueva['hora'], bcv, fuente, p2p, brecha, banco))
    return 0


if __name__ == '__main__':
    sys.exit(main())
