# Lótus: arquitetura

Controle de irrigação para **duas casas independentes**, cada uma com seu próprio
controlador e sua própria bomba. As duas usam o **mesmo app Android** (Kotlin nativo),
que fica para a etapa final.

| | **Site ESP** | **Site CLP** |
|---|---|---|
| Objetivo | Custo baixo | Reaproveitar material parado |
| Cérebro | ESP32 + placa de 8 relés | CLP Delta DVP20SX211R + ESP32 como gateway |
| Bomba | Contator (liga/desliga) | Inversor Metaltex IF10-203-1 (pressão constante) |
| Firmware | ESPHome `sprinkler` | ESPHome `sprinkler` + `modbus_controller`; ladder no CLP |

Os dois sites não compartilham hardware nem rede. A única coisa em comum é o
**contrato de comunicação com o app** (seção 3), para que um único app atenda os dois.

---

## 1. Site ESP: ESP32 + relés

### 1.1 Quadro físico

```
 Rede 220V
   │
   ├─ DR + disjuntor ──┬───────────────────────────────────────────┐
   │                   │                                           │
   │           Transformador 220V→24VAC                   Disjuntor-motor
   │           (50VA / ~2A)                               (ex. WEG MPW, ajustado
   │                   │ 24VAC                             na corrente da bomba)
   │                   │                                           │
   │   Fonte 5V ───────┼──────────────┐                     Contator (bobina 24VAC)
   │   (ESP32)         │              │                            │ contatos de força
   │                   │       ┌──────┴──────────┐                 │
   │             ┌─────┴────┐  │ Placa 8 relés   │            BOMBA 220V
   │             │  ESP32   ├──┤ (opto, 3,3V)    │
   │             │ ESPHome  │  │ R1..R7 → zonas  │── 24VAC → válvulas 1..7
   │             └─┬──┬──┬──┘  │ R8 → bobina ────┼── via boia (contato em série)
   │               │  │  │     └─────────────────┘
   │   sensor chuva┘  │  └ botões por zona (entradas)
   │        boia nível┘ (também lida pelo ESP)
   │
   └─ Wi-Fi da casa ──► internet
```

- **Válvulas:** 7 zonas (R1–R7). O R8 fica para a bomba.
- **Botões:** os 8 botões do painel (7 zonas + parar tudo) entram por um expansor I2C **PCF8574**,
  que usa só 2 pinos do ESP32. O sensor de chuva e a boia vão direto em GPIOs.
- **Lista de compras:** [`site/componentes.html`](../site/componentes.html), com os dados em `site/dados-componentes.js`.
- **Bomba:** o R8 aciona a bobina de um **contator com bobina 24VAC**. Assim o 220V fica
  só no transformador e nos contatos de força do contator. A placa de relés continua sem 220V.
- **Transformador:** suba para **~50VA (2A)**. O 1A da especificação original servia só
  para as válvulas. O contator puxa um pico grande ao fechar.
- **Proteção contra rodar a seco:** o contato da **boia** (ou chave de nível) vai **em série
  com a bobina do contator**. Isso é uma trava física e funciona mesmo se o firmware errar.
  A boia também vai a uma entrada do ESP32, que usa a informação para avisar no app.
- **Sequência:** o componente `sprinkler` do ESPHome tem `pump_switch` por válvula.
  Ele abre a válvula, espera e liga a bomba; na parada, desliga a bomba antes de fechar a
  válvula. Assim a bomba nunca bate contra o registro fechado.
- **Bomba (ainda não comprada):** uma monofásica 220V atende. Ela deve ser dimensionada pela
  vazão da maior zona e pela pressão que os gotejadores ou aspersores pedem.

---

## 2. Site CLP: CLP + inversor

### 2.1 Equipamentos

| Item | Dados relevantes |
|---|---|
| **CLP Delta DVP20SX211R** | 24Vdc. 8 entradas digitais (X0–X7). **6 saídas a relé** Y0–Y5 (1,5A/250VAC), com comuns C0 = Y0–Y2 e C1 = Y3–Y5. 4 entradas analógicas e 2 saídas analógicas. **COM1 RS-232, COM2 RS-485**, USB. **Não tem rede.** |
| **Inversor Metaltex IF10-203-1** (catálogo em `~/Downloads/if10.pdf`) | Entrada **monofásica 220V, 16A**. Saída **trifásica 220V, 11A, 3cv/2,2kW**. Entradas digitais S1, S2, FWD, REV. **AVI aceita 0–10V ou 4–20mA** (chave seletora I/V). **Relé NA RA/RC**, 250VAC/3A. **PID integrado. Modbus-RTU em RS-485.** |

A configuração, os parâmetros e o mapa Modbus do inversor estão em
[`docs/hardware/metaltex-if10.md`](hardware/metaltex-if10.md). Os PDFs originais ficam em `docs/manuais/`.

### 2.2 O que o inversor muda na escolha da bomba

- A bomba **precisa ser trifásica 220V e ter até 3cv**. O inversor recebe monofásico e entrega
  trifásico, então a casa pode ser monofásica normalmente. Na prática isso é uma vantagem:
  bomba trifásica costuma ser mais barata e mais robusta.
- O inversor tem um **modo pronto de pressão constante para bomba** (P600–P657). Um transdutor
  de pressão **4–20mA** vai no AVI (chave em **I**). O próprio inversor cuida de:
  - manter a pressão no setpoint (em bar);
  - parar por **falta d'água** (a pressão não sobe com a bomba rodando);
  - parar por pressão alta ou baixa;
  - parar se perder o sensor;
  - **repouso** quando não há consumo.

  O CLP só manda ligar e desligar.
- **Atenção:** o inversor sai de fábrica em **50Hz** (P105 e P110). É preciso mudar para 60Hz.
- A alimentação do inversor pede disjuntor de **20A** e cabo de 2,5mm² ou mais (corrente de entrada 16A).

### 2.3 Quadro físico

```
 Rede 220V monofásica
   │
   ├─ DR + disjuntor 20A ── INVERSOR IF10 (L1,L2) ── U,V,W ──► BOMBA TRIFÁSICA 220V
   │                          │  ▲      ▲     │
   │                          │  │FWD   │AVI  │RA/RC (relé de falha/rodando)
   │                          │  │      │     │
   ├─ Fonte 24Vdc ────────┐   │  │   transdutor de pressão 4–20mA (na tubulação)
   │                      │   │  │                 │
   ├─ Transf. 220V→24VAC ─┼───┼──┼─────────┐       │(opcional: em série com I0 do CLP)
   │                      │   │  │         │       │
   │                 ┌────┴───┴──┴───┐     │       │
   │                 │ CLP DVP20SX2  │◄────┼───────┘
   │                 │ Y0–Y4 ────────┼──24VAC──► válvulas 1..5
   │                 │ Y5 ───────────┼──► FWD do inversor
   │                 │ X0..X7 ◄──────┼── vazão, chuva, boia, botões, falha
   │                 │ COM2 RS-485   │
   │                 └──────┬────────┘
   │                        │ par trançado (Modbus RTU)
   │                 ┌──────┴────────┐
   ├─ Fonte 5V ──────┤ ESP32 + MAX485│  ◄── gateway: único elemento com rede
   │                 │ ESPHome       │
   │                 └──────┬────────┘
   └─ Wi-Fi da casa ────────┘──► internet
```

### 2.4 Mapa de E/S proposto

| Ponto | Uso |
|---|---|
| Y0–Y4 | Zonas 1–5 (24VAC nos comuns C0/C1) |
| Y5 | RUN da bomba → FWD do inversor |
| X0 | Sensor de vazão por pulso (contador rápido): detecta tubo estourado ou zona sem água |
| X1 | Sensor de chuva |
| X2 | Boia/nível (**proteção contra rodar a seco**) |
| X3 | Botão "parar tudo" |
| X4 | Botão "avançar zona" |
| X5 | Chave Auto/Manual |
| X6 | Falha do inversor (RA/RC configurado como saída de falha) |
| X7 | Reserva |
| I0 (opcional) | Mesmo laço 4–20mA do transdutor, em série com o AVI, para o CLP também ler a pressão |

Mais zonas exigem um módulo de expansão de saídas DVP-S na porta lateral.

### 2.5 Quem decide o quê

- **Inversor:** controla a pressão (PID) e protege o motor.
- **CLP:** cuida da segurança e do modo manual. Liga as saídas e aplica as travas:
  - bomba só com uma válvula aberta;
  - bomba desliga com boia baixa, falha do inversor ou vazão zero;
  - tempo máximo por zona;
  - watchdog: se o ESP32 parar de dar sinal, o CLP fecha as zonas abertas remotamente;
  - o modo Manual ignora comandos remotos.
- **ESP32:** cuida da agenda e da conexão. Roda o mesmo ESPHome `sprinkler` do site ESP, mas
  cada "válvula" é um **pedido** escrito em um bit M do CLP via Modbus. Ele nunca escreve direto
  nas saídas Y.

### 2.6 ESP32 ↔ CLP

- **Física:** COM2 RS-485 do CLP ↔ módulo MAX485/MAX3485 no ESP32. O ESP32 é mestre
  Modbus RTU e o CLP é escravo no endereço 1.
- **Configuração:** o COM2 sai de fábrica em Modbus ASCII 9600 7E1 e precisa ir para **RTU 8N1**
  no ladder (D1120/M1120/M1143, **a confirmar** no manual de programação). Detalhes do CLP em [`docs/hardware/delta-dvp20sx2.md`](hardware/delta-dvp20sx2.md). A USB fica livre para programação (ISPSoft/WPLSoft).
- **Endereços Modbus Delta DVP:** X = 0x0400, Y = 0x0500, M = 0x0800, D = 0x1000.

| Endereço | Direção | Conteúdo |
|---|---|---|
| M100–M104 | ESP → CLP | Pedido de zona 1–5 |
| M110 | ESP → CLP | Parar tudo |
| M111 | ESP → CLP | Atraso por chuva |
| D100 | ESP → CLP | Heartbeat |
| D200 | CLP → ESP | Bitmask de zonas abertas de fato |
| D201 | CLP → ESP | Estado (0 ocioso, 1 irrigando, 2 manual, 3 falha) |
| D202 | CLP → ESP | Bits de falha (seco, inversor, vazão, watchdog) |
| D203 | CLP → ESP | Pressão (kPa), se usar I0 |
| D204–D206 | CLP → ESP | Vazão e totalizador de litros |

**Inversor no mesmo barramento, só para leitura:** o inversor entra como escravo 2
(P701 = 3 para 8N1 RTU, P702 = 2). O ESP32 lê dele frequência, corrente, potência, alarmes
e, se o teste confirmar, a pressão (0007H). Assim o app mostra a pressão sem precisar do I0 do CLP.
O ESP32 **nunca escreve** no inversor: o comando continua pela fiação do CLP.

---

## 3. Comunicação com o app

### 3.1 O problema

São duas casas, cada uma com seu Wi-Fi. O celular precisa falar com cada uma estando
**em qualquer lugar**. O roteador de casa bloqueia conexões que vêm de fora, então o
celular não consegue chamar o ESP32 diretamente pela internet.

### 3.2 A solução: um ponto de encontro na nuvem (broker MQTT)

```
  Site ESP                        Nuvem                         Site CLP
 ┌────────────┐              ┌──────────────┐               ┌────────────┐
 │ ESP32 (ESP)│──── sai ────►│ Broker MQTT  │◄──── sai ─────│ ESP32 (CLP)│
 └────────────┘   (TLS)      │ (EMQX        │    (TLS)      └────────────┘
                             │  Serverless, │
                             │ plano grátis)│
                             └──────▲───────┘
                                    │ sai (TLS)
                              ┌─────┴──────┐
                              │ App Android│  (4G ou qualquer Wi-Fi)
                              └────────────┘
```

O broker funciona como uma caixa postal:

- Os dois ESP32 e o celular **abrem a conexão de dentro para fora**. Isso não exige abrir porta
  no roteador, configurar DNS ou ter servidor em casa.
- O ESP32 **publica** o estado ("zona 3 ligada, faltam 4 min") e **escuta** comandos.
- O app **escuta** o estado e **publica** comandos.
- Cada casa tem **usuário e senha próprios** no broker e só enxerga os próprios tópicos.
- A agenda roda no ESP32. **Se a internet cair, a irrigação continua.** O app só deixa de ver
  e comandar até a conexão voltar, e os botões físicos continuam funcionando.
- O plano gratuito do EMQX Serverless sobra para dois ESP32 e alguns celulares. O HiveMQ Cloud
  Serverless, que era a outra opção, parou de ser vendido em 30/09/2026.
- O ESPHome suporta MQTT com TLS no framework ESP-IDF.

Alternativas descartadas:
- **Só rede local** (app falando direto com o ESP32): não funciona fora de casa, e as duas casas
  precisam do acesso remoto.
- **Home Assistant em cada casa:** exige um computador ligado em cada casa e torna o app
  próprio desnecessário.

### 3.3 Contrato `lotus/v1`

```
lotus/v1/{site}/status            → "online" | "offline"                                (retained, LWT)
lotus/v1/{site}/info              → {type, fw, zones, hasPressure, hasFlow, hasButtons}  (retained)
lotus/v1/{site}/state             → {mode, activeZone, remainingS, nextZone, rainDelayUntil, fault, ts} (retained)
lotus/v1/{site}/zone/{n}/state    → {on, name, defaultDurationS}                        (retained)
lotus/v1/{site}/sensors           → {rain, level, pressureKpa?, flowLpm?}                (retained)
lotus/v1/{site}/schedule          → {enabled, days, starts}                              (retained)

lotus/v1/{site}/cmd               ← {id, op, ...}  start_zone | start_cycle | stop_all | pause | resume
                                                   rain_delay | set_zone | set_schedule
lotus/v1/{site}/cmd/ack           → {id, ok, error?}
```

- `{site}` = `esp`, `clp`. O app pode ter os dois cadastrados ou só um.
- O app lê o `info` e mostra só o que o site tem. Pressão e vazão aparecem só no site CLP.
- O `ack` informa se o comando foi recusado (exemplo: o site CLP em modo Manual).
- Especificação completa, com campos, erros e exemplos: [`CONTRATO-MQTT.md`](CONTRATO-MQTT.md).
- Configuração do broker e das permissões: [`broker/README.md`](../broker/README.md).

---

## 4. Ordem de execução

1. **Site ESP:** bancada com ESP32 + relés + ESPHome `sprinkler` + LEDs no lugar das válvulas.
2. **Broker:** conta no EMQX e ESP32 publicando no `lotus/v1`, testado com `tools/lotus_mqtt.py`.
   O firmware (`firmware/lotus-esp.yaml`) e o simulador já existem; falta criar a conta e gravar o ESP32.
3. **Site ESP:** escolha da bomba, hidráulica e instalação.
4. **Site CLP:** parametrizar o IF10 (`docs/hardware/metaltex-if10.md`), ladder no CLP, teste Modbus pelo PC (mbpoll/QModMaster).
5. **Site CLP:** gateway ESP32 com o mesmo contrato, depois inversor, bomba trifásica e transdutor.
6. **App Android (Kotlin)** em cima do `lotus/v1`.

## 5. Em aberto

- [ ] Origem da água em cada casa (poço ou caixa). Define a boia e a escolha das bombas.
- [ ] Número de zonas em cada casa e vazão da maior zona.
- [ ] Testar na bancada se o registrador 0007H do IF10 devolve a pressão (P007).
- [ ] Manual de programação do CLP Delta DVP-SX2 (ver `docs/manuais/README.md`).
- [ ] Boia do site ESP com **dois contatos** (ou um relé auxiliar): um em série com a bobina do
      contator e outro, seco, para a entrada do ESP32 (GPIO33). Não dá para ler o mesmo contato
      que está no circuito de 24VAC.
- [ ] O site CLP é monofásica? Se for bifásica 220V, o resultado é o mesmo para o inversor.
