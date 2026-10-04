#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["paho-mqtt>=2.1"]
# ///
"""Ferramenta de linha de comando para o contrato lotus/v1.

    tools/lotus_mqtt.py ouvir   [site]                    mostra tudo o que passa no broker
    tools/lotus_mqtt.py cmd     <site> <op> [campo=valor ...]
    tools/lotus_mqtt.py simular <site> [--zonas N] [--rapido]

Exemplos:
    tools/lotus_mqtt.py cmd esp start_zone zone=2 durationS=300
    tools/lotus_mqtt.py cmd esp set_schedule enabled=true days=127 starts=[360,1080]
    tools/lotus_mqtt.py simular esp --rapido

A conexão vem de variáveis de ambiente ou de um arquivo .env na raiz do repositório:
    LOTUS_MQTT_HOST, LOTUS_MQTT_PORT (8883), LOTUS_MQTT_USER, LOTUS_MQTT_PASS,
    LOTUS_MQTT_TLS (1), LOTUS_MQTT_CA (opcional: caminho da CA; sem ele usa as CAs do sistema)
"""

import argparse
import json
import os
import ssl
import sys
import threading
import time
import uuid
from pathlib import Path

import paho.mqtt.client as mqtt

RAIZ = "lotus/v1"


def carregar_env():
    env = Path(__file__).resolve().parent.parent / ".env"
    if not env.exists():
        return
    for linha in env.read_text().splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


def conectar(client_id, will=None):
    host = os.environ.get("LOTUS_MQTT_HOST")
    if not host:
        sys.exit("defina LOTUS_MQTT_HOST (veja broker/README.md)")
    tls = os.environ.get("LOTUS_MQTT_TLS", "1") != "0"
    porta = int(os.environ.get("LOTUS_MQTT_PORT", "8883" if tls else "1883"))

    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    if os.environ.get("LOTUS_MQTT_USER"):
        c.username_pw_set(os.environ["LOTUS_MQTT_USER"], os.environ.get("LOTUS_MQTT_PASS"))
    if tls:
        c.tls_set(ca_certs=os.environ.get("LOTUS_MQTT_CA") or None, tls_version=ssl.PROTOCOL_TLS_CLIENT)
    if will:
        c.will_set(*will)

    conectado = threading.Event()

    def on_connect(client, userdata, flags, rc, props):
        if rc.is_failure:
            sys.exit(f"broker recusou a conexão: {rc}")
        conectado.set()

    c.on_connect = on_connect
    c.connect(host, porta, keepalive=30)
    c.loop_start()
    if not conectado.wait(10):
        sys.exit(f"sem resposta de {host}:{porta}")
    return c


def valor(texto):
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        return texto


# ---------------------------------------------------------------- ouvir

def ouvir(args):
    c = conectar(f"lotus-ouvir-{uuid.uuid4().hex[:6]}")
    filtro = f"{RAIZ}/{args.site}/#" if args.site else f"{RAIZ}/#"

    def on_message(client, userdata, msg):
        retido = " (retido)" if msg.retain else ""
        print(f"{time.strftime('%H:%M:%S')} {msg.topic}{retido}  {msg.payload.decode(errors='replace')}", flush=True)

    c.on_message = on_message
    c.subscribe(filtro, qos=1)
    print(f"ouvindo {filtro} (Ctrl+C para sair)", file=sys.stderr)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


# ---------------------------------------------------------------- cmd

def cmd(args):
    corpo = {"id": uuid.uuid4().hex[:12], "op": args.op}
    for par in args.campos:
        if "=" not in par:
            sys.exit(f"campo sem '=': {par}")
        k, v = par.split("=", 1)
        corpo[k] = valor(v)

    c = conectar(f"lotus-cmd-{corpo['id']}")
    resposta = threading.Event()

    def on_message(client, userdata, msg):
        try:
            ack = json.loads(msg.payload)
        except json.JSONDecodeError:
            return
        if ack.get("id") == corpo["id"]:
            print(json.dumps(ack, ensure_ascii=False))
            resposta.ok = ack.get("ok")
            resposta.set()

    c.on_message = on_message
    c.subscribe(f"{RAIZ}/{args.site}/cmd/ack", qos=1)
    time.sleep(0.3)
    c.publish(f"{RAIZ}/{args.site}/cmd", json.dumps(corpo), qos=1, retain=False).wait_for_publish(5)
    if not resposta.wait(10):
        sys.exit("sem ack em 10s: o quadro está online? (veja o tópico status)")
    sys.exit(0 if resposta.ok else 1)


# ---------------------------------------------------------------- simular

class Simulador:
    """Imita um quadro do site ESP: mesma lógica de fila, agenda e ack do firmware."""

    def __init__(self, site, zonas, escala):
        self.site = site
        self.base = f"{RAIZ}/{site}"
        self.zonas = zonas
        self.escala = escala  # segundos simulados por segundo real
        self.duracao = [600] * zonas
        self.nomes = [f"Zona {i + 1}" for i in range(zonas)]
        self.ativa = None  # índice 0..zonas-1
        self.restante = 0.0
        self.fila = []  # [(zona, duração)]
        self.pausada = None  # (zona, restante, fila)
        self.chuva_ate = 0
        self.agenda = {"enabled": False, "days": 127, "starts": [360]}
        self.trava = threading.Lock()
        self.c = conectar(f"lotus-sim-{site}", will=(f"{self.base}/status", "offline", 1, True))
        self.c.on_message = self.on_message
        self.c.subscribe(f"{self.base}/cmd", qos=1)
        self.c.publish(f"{self.base}/status", "online", qos=1, retain=True)
        self.ultimo_state = None
        self.ultimo_envio = 0.0
        self.publicar_tudo()

    def pub(self, sufixo, corpo, retido=True):
        self.c.publish(f"{self.base}/{sufixo}", json.dumps(corpo, ensure_ascii=False), qos=1, retain=retido)

    def publicar_tudo(self):
        self.pub("info", {"type": "esp32-relay", "fw": "sim", "zones": self.zonas,
                          "hasPressure": False, "hasFlow": False, "hasButtons": False})
        self.pub("schedule", self.agenda)
        self.pub("sensors", {"rain": False, "level": "ok"})
        for i in range(self.zonas):
            self.publicar_zona(i)
        self.publicar_state(forcar=True)

    def publicar_zona(self, i):
        self.pub(f"zone/{i + 1}/state", {"on": self.ativa == i, "name": self.nomes[i],
                                         "defaultDurationS": self.duracao[i]})

    def publicar_state(self, forcar=False):
        modo = "running" if self.ativa is not None else ("paused" if self.pausada else "idle")
        proxima = self.fila[0][0] + 1 if self.fila else None
        chuva = self.chuva_ate if self.chuva_ate > time.time() else None
        assinatura = (modo, self.ativa, proxima, chuva)
        agora = time.monotonic()
        if not forcar and assinatura == self.ultimo_state and not (
                self.ativa is not None and agora - self.ultimo_envio >= 15):
            return
        self.pub("state", {"mode": modo,
                           "activeZone": self.ativa + 1 if self.ativa is not None else None,
                           "remainingS": round(self.restante) if self.ativa is not None else None,
                           "nextZone": proxima, "rainDelayUntil": chuva, "fault": None,
                           "ts": int(time.time())})
        self.ultimo_state = assinatura
        self.ultimo_envio = agora

    def abrir(self, zona, dur):
        anterior = self.ativa
        self.ativa, self.restante = zona, float(dur)
        if anterior is not None and anterior != zona:
            self.publicar_zona(anterior)
        self.publicar_zona(zona)
        print(f"  zona {zona + 1} aberta por {dur}s", flush=True)

    def parar(self):
        anterior = self.ativa
        self.ativa, self.fila, self.pausada = None, [], None
        if anterior is not None:
            self.publicar_zona(anterior)

    def executar(self, x):
        op = x.get("op")
        if not x.get("id") or not op:
            return "bad_request"
        if op == "start_zone":
            z, dur = x.get("zone"), x.get("durationS")
            if not isinstance(z, int) or not 1 <= z <= self.zonas:
                return "invalid_zone"
            if dur is not None and (not isinstance(dur, int) or not 0 <= dur <= 86400):
                return "invalid_duration"
            self.parar()
            self.abrir(z - 1, dur or self.duracao[z - 1])
        elif op == "start_cycle":
            self.parar()
            self.fila = [(i, self.duracao[i]) for i in range(1, self.zonas)]
            self.abrir(0, self.duracao[0])
        elif op == "stop_all":
            self.parar()
        elif op == "pause":
            if self.ativa is not None:
                self.pausada = (self.ativa, self.restante, self.fila)
                z = self.ativa
                self.ativa, self.fila = None, []
                self.publicar_zona(z)
        elif op == "resume":
            if self.pausada:
                z, r, fila = self.pausada
                self.pausada = None
                self.fila = fila
                self.abrir(z, r)
        elif op == "rain_delay":
            h = x.get("hours")
            if not isinstance(h, (int, float)) or not 0 <= h <= 336:
                return "invalid_hours"
            self.chuva_ate = time.time() + h * 3600 if h else 0
            if h:
                self.parar()
        elif op == "set_zone":
            z, dur = x.get("zone"), x.get("defaultDurationS")
            if not isinstance(z, int) or not 1 <= z <= self.zonas:
                return "invalid_zone"
            if not isinstance(dur, int) or not 1 <= dur <= 86400:
                return "invalid_duration"
            self.duracao[z - 1] = dur
            self.publicar_zona(z - 1)
        elif op == "set_schedule":
            en, dias, ini = x.get("enabled"), x.get("days"), x.get("starts")
            if (not isinstance(en, bool) or not isinstance(dias, int) or not 0 <= dias <= 127
                    or not isinstance(ini, list) or len(ini) > 4
                    or not all(isinstance(m, int) and 0 <= m < 1440 for m in ini)):
                return "bad_request"
            self.agenda = {"enabled": en, "days": dias, "starts": ini}
            self.pub("schedule", self.agenda)
        else:
            return "unknown_op"
        return None

    def on_message(self, client, userdata, msg):
        try:
            x = json.loads(msg.payload)
            if not isinstance(x, dict):
                raise ValueError
        except ValueError:
            x = {}
        with self.trava:
            erro = self.executar(x)
            print(f"cmd {x.get('id')} {x.get('op')} -> {erro or 'ok'}", flush=True)
            ack = {"id": x.get("id", ""), "ok": erro is None}
            if erro:
                ack["error"] = erro
            self.pub("cmd/ack", ack, retido=False)
            self.publicar_state()

    def rodar(self):
        anterior = time.monotonic()
        while True:
            time.sleep(0.25)
            agora = time.monotonic()
            passo = (agora - anterior) * self.escala
            anterior = agora
            with self.trava:
                if self.ativa is not None:
                    self.restante -= passo
                    if self.restante <= 0:
                        z = self.ativa
                        self.ativa = None
                        self.publicar_zona(z)
                        print(f"  zona {z + 1} fechada", flush=True)
                        if self.fila:
                            self.abrir(*self.fila.pop(0))
                self.publicar_state()


def simular(args):
    sim = Simulador(args.site, args.zonas, 60.0 if args.rapido else 1.0)
    print(f"simulando {args.site} com {args.zonas} zonas"
          f"{' (1 min por segundo)' if args.rapido else ''}. Ctrl+C para sair.", file=sys.stderr)
    try:
        sim.rodar()
    except KeyboardInterrupt:
        sim.c.publish(f"{sim.base}/status", "offline", qos=1, retain=True).wait_for_publish(3)


def main():
    carregar_env()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="acao", required=True)

    o = sub.add_parser("ouvir", help="mostra as mensagens do broker")
    o.add_argument("site", nargs="?")
    o.set_defaults(f=ouvir)

    k = sub.add_parser("cmd", help="envia um comando e espera o ack")
    k.add_argument("site")
    k.add_argument("op")
    k.add_argument("campos", nargs="*", metavar="campo=valor")
    k.set_defaults(f=cmd)

    s = sub.add_parser("simular", help="finge ser um quadro")
    s.add_argument("site")
    s.add_argument("--zonas", type=int, default=7)
    s.add_argument("--rapido", action="store_true", help="1 minuto simulado por segundo")
    s.set_defaults(f=simular)

    args = p.parse_args()
    args.f(args)


if __name__ == "__main__":
    main()
