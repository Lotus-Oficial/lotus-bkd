# Contrato `lotus/v1`

É o que os quadros (ESP32) e o app trocam pelo broker MQTT. Os dois sites falam o mesmo
contrato; o app lê o `info` de cada um e mostra só o que aquele site tem.

- `{site}`: `esp` (ESP32 + relés) ou `clp` (CLP Delta + inversor).
- Payloads em JSON UTF-8, exceto `status`, que é texto puro.
- Zonas numeradas a partir de **1**.
- Tempos em segundos. Datas em epoch Unix (segundos, UTC).
- Horários da agenda em **minutos desde a meia-noite, no fuso da casa** (`America/Sao_Paulo`).
- Campos opcionais ausentes ou `null` significam "não se aplica" ou "nada no momento".
- O app se inscreve em `lotus/v1/{site}/#`, uma inscrição por site. O EMQX **nega a inscrição
  inteira** se o filtro for mais amplo que o permitido ao usuário (ex.: `app-esp` em `lotus/v1/#`).
  O Mosquitto local é mais tolerante: só filtra as mensagens. Não use ele como referência para isso.

## Tópicos publicados pelo quadro

Todos **retidos** e com **QoS 1**: quem se inscreve recebe na hora o último valor.
São publicados quando mudam e de novo a cada reconexão ao broker.

| Tópico | Payload |
|---|---|
| `lotus/v1/{site}/status` | `online` \| `offline` (o `offline` é o LWT: o broker publica sozinho se o quadro sumir) |
| `lotus/v1/{site}/info` | `{type, fw, zones, hasPressure, hasFlow, hasButtons}` |
| `lotus/v1/{site}/state` | `{mode, activeZone, remainingS, nextZone, rainDelayUntil, fault, ts}` |
| `lotus/v1/{site}/zone/{n}/state` | `{on, name, defaultDurationS}` |
| `lotus/v1/{site}/sensors` | `{rain, level, pressureKpa?, flowLpm?}` |
| `lotus/v1/{site}/schedule` | `{enabled, days, starts}` |

### `info`

```json
{"type": "esp32-relay", "fw": "0.1.0", "zones": 7, "hasPressure": false, "hasFlow": false, "hasButtons": true}
```

`type`: `esp32-relay` (site ESP) ou `plc-delta` (site CLP).

### `state`

```json
{"mode": "running", "activeZone": 3, "remainingS": 412, "nextZone": 4,
 "rainDelayUntil": null, "fault": null, "ts": 1791230400}
```

| Campo | Valores |
|---|---|
| `mode` | `idle`, `running`, `paused` (site CLP: também `manual`) |
| `activeZone` | zona aberta agora, ou `null` |
| `remainingS` | segundos restantes da zona ativa, ou `null` |
| `nextZone` | próxima zona do ciclo ou da fila, ou `null` |
| `rainDelayUntil` | epoch até quando a agenda está suspensa, ou `null` |
| `fault` | `null`, `dry` (nível baixo). Site CLP: também `inverter`, `no_flow`, `watchdog` |
| `ts` | hora do quadro no envio (ausente se o relógio ainda não sincronizou) |

Durante a irrigação o `state` é republicado a cada 15s. Entre uma publicação e outra,
o app conta o `remainingS` para baixo sozinho.

### `sensors`

`rain`: `true` se o sensor de chuva está molhado. `level`: `ok` ou `low`.
`pressureKpa` e `flowLpm` só existem no site CLP.

### `schedule`

```json
{"enabled": true, "days": 127, "starts": [360, 1080]}
```

- `days`: bitmask, bit 0 = domingo ... bit 6 = sábado (`127` = todos os dias, `62` = seg a sex).
- `starts`: até 4 horários de início do ciclo completo (`360` = 06:00).

O ciclo agendado roda todas as zonas em sequência, cada uma pelo seu `defaultDurationS`.
Ele é pulado se o quadro já estiver irrigando, se houver atraso por chuva, se o sensor de
chuva estiver molhado ou se o nível estiver baixo.

## Comandos (app → quadro)

Publicados em `lotus/v1/{site}/cmd`, **QoS 1, nunca retidos**. Um comando retido seria
executado de novo a cada reconexão do quadro.

Todo comando tem um `id` (texto, único por comando; um UUID serve). O quadro responde em
`lotus/v1/{site}/cmd/ack` (QoS 1, não retido):

```json
{"id": "7f3c...", "ok": true}
{"id": "7f3c...", "ok": false, "error": "fault_dry"}
```

| `op` | Campos | Efeito |
|---|---|---|
| `start_zone` | `zone`, `durationS?` | Abre só essa zona. Sem `durationS`, usa o padrão da zona. Interrompe o que estiver rodando. |
| `start_cycle` | | Ciclo completo, todas as zonas em sequência |
| `stop_all` | | Para tudo e limpa a fila |
| `pause` | | Pausa a zona atual (bomba e válvula desligam) |
| `resume` | | Retoma de onde pausou |
| `rain_delay` | `hours` | Suspende a agenda por `hours` horas (máx. 336) e para o que estiver rodando. `0` cancela. |
| `set_zone` | `zone`, `defaultDurationS` | Muda a duração padrão da zona (1 s a 24 h) |
| `set_schedule` | `enabled`, `days`, `starts` | Substitui a agenda inteira (mesmo formato do tópico `schedule`) |

Erros possíveis no `ack`:

| `error` | Quando |
|---|---|
| `bad_request` | JSON sem `id`/`op`, ou campos com formato errado |
| `unknown_op` | `op` não existe |
| `invalid_zone` | zona fora de 1..`zones` |
| `invalid_duration` | duração fora do limite |
| `invalid_hours` | `hours` fora de 0..336 |
| `fault_dry` | nível baixo: o quadro não abre zona sem água |
| `no_time` | relógio ainda não sincronizado (o `rain_delay` precisa da hora) |
| `manual` | site CLP em modo Manual: comandos remotos são ignorados |

Se nenhum `ack` chegar em ~10s, o app deve tratar o quadro como fora do ar (veja o `status`).

## Exemplos

```sh
# tudo o que a casa publica
mosquitto_sub -h $HOST -p 8883 --capath /etc/ssl/certs -u app-admin -P $SENHA -v -t 'lotus/v1/esp/#'

# abrir a zona 2 por 5 minutos
mosquitto_pub -h $HOST -p 8883 --capath /etc/ssl/certs -u app-admin -P $SENHA -q 1 \
  -t lotus/v1/esp/cmd -m '{"id":"t1","op":"start_zone","zone":2,"durationS":300}'
```

O script `tools/lotus_mqtt.py` faz o mesmo sem precisar do mosquitto e também simula um quadro
(veja `broker/README.md`).
