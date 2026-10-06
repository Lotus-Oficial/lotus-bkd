# Lótus: funcionalidades

O que o Lótus já faz, o que está projetado e o que ainda é ideia.
Aqui **canteiro** e **zona** são a mesma coisa: um trecho do quintal regado por uma válvula.

| Marca | Significado |
|---|---|
| ✅ | Funciona no firmware e foi testado na bancada |
| 🧪 | Está no firmware, mas falta testar com o equipamento real |
| 📐 | Projetado em [`ARCHITECTURE.md`](ARCHITECTURE.md), sem código ainda |
| 💡 | Ideia: falta decidir hardware, contrato e regras |

## Resumo

| Funcionalidade | Site ESP | Site CLP |
|---|---|---|
| [Até 7 válvulas solenoides por casa](#1-válvulas-solenoides-por-zona) | ✅ 7 zonas | 📐 5 zonas |
| [Agenda no quadro, que roda sem internet](#2-agenda-e-comandos-remotos) | ✅ | 📐 |
| [Comando pelo app via MQTT (`lotus/v1`)](#2-agenda-e-comandos-remotos) | ✅ | 📐 |
| [Botões físicos no painel](#3-botões-no-painel) | 🧪 | 📐 |
| [Não regar quando está chovendo](#4-chuva-não-regar-quando-chove) | 🧪 | 📐 |
| [Caixa d'água: falta de água para tudo](#5-caixa-dágua-de-cada-casa) | 🧪 | 📐 |
| [Caixa d'água: ativar, desativar e controlar](#5-caixa-dágua-de-cada-casa) | 💡 | 💡 |
| [Pressão controlada](#6-pressão) | 💡 | 📐 pressão constante no inversor |
| [Pressão diferente por zona](#6-pressão) | 💡 | 💡 |
| [Vazão e totalizador de litros](#7-vazão) | — | 📐 |
| [Umidade do solo, N sensores por canteiro](#8-umidade-do-solo-por-canteiro) | 💡 | 💡 |
| [Tempo: nublado, ensolarado, previsão](#9-tempo-nublado-ensolarado-previsão) | 💡 | 💡 |
| [Canteiros dentro de canteiros](#10-canteiros-dentro-de-canteiros-válvulas-aninhadas) | 💡 | 💡 |

---

## Implementado

### 1. Válvulas solenoides por zona

✅ **Site ESP.** Sete válvulas solenoides 24VAC (Rain Bird 100-HV, normalmente fechadas),
uma por zona, nos relés R1–R7. O R8 liga a bomba. Cada zona tem nome e duração padrão,
que o app muda com `set_zone`.

A sequência evita golpe na bomba: abre a válvula, espera 3s, liga a bomba. Na parada,
desliga a bomba, espera 3s, fecha a válvula. No ciclo completo, as zonas se sobrepõem 2s
para a bomba nunca ficar contra registro fechado.

Na bancada, LEDs no lugar das válvulas confirmaram a sequência. Só a primeira válvula foi comprada.

📐 **Site CLP.** Cinco zonas nas saídas Y0–Y4 do CLP. Mais zonas exigem módulo de expansão DVP-S.

### 2. Agenda e comandos remotos

✅ **Site ESP.** A agenda fica gravada no ESP32 e sobrevive a reboot: dias da semana e até
quatro horários de início por dia. Cada horário roda o ciclo completo, todas as zonas em sequência.
Se a internet ou o broker caírem, a agenda continua rodando.

Pelo app (contrato [`lotus/v1`](CONTRATO-MQTT.md)): ligar uma zona por um tempo, rodar o
ciclo, parar tudo, pausar, retomar, mudar a duração de uma zona e trocar a agenda.
Cada comando recebe um `ack` com `ok` ou o motivo da recusa.

Testado com `tools/lotus_mqtt.py` contra o EMQX na nuvem.

### 3. Botões no painel

🧪 **Site ESP.** Oito botões via expansor PCF8574: os botões 1–7 ligam e desligam a zona
correspondente, e o 8 para tudo. Funcionam sem internet. O código está pronto; falta montar o painel.

### 4. Chuva: não regar quando chove

🧪 **Site ESP.** Há duas formas, e as duas estão no firmware:

- **Sensor de chuva** (Hunter Mini-Clik, contato seco no GPIO32). Molhado, a agenda pula o
  ciclo; se começar a chover no meio da rega, o quadro para tudo. O estado vai para o app em
  `sensors.rain`. O sensor ainda não foi comprado.
- **Atraso por chuva** pelo app (`rain_delay`): suspende a agenda por até 14 dias e para o
  que estiver rodando. Serve quando choveu e o solo ainda está molhado, mesmo com o sensor já seco.

A parada vale para qualquer rega em andamento ou pausada, agendada ou manual, e acontece só
na passagem de seco para molhado. Com o sensor já molhado, comandos manuais pelo app ou pelos
botões continuam funcionando: é a pessoa decidindo regar mesmo com chuva.

**Instalação do sensor.** O quadro não distingue chuva de água do aspersor: se a rega molhar o
sensor, ela para no meio e as próximas regas agendadas são puladas até os discos secarem, o que
leva horas. O Mini-Clik só fecha o contato depois de acumular alguns milímetros de água (regulável
de ~3 a 25 mm), então respingo e névoa não bastam; jato direto basta. Por isso:

- no alto e a céu aberto (beiral, calha ou poste), fora do alcance de **todas** as zonas.
  Ligue cada zona uma vez e confira até onde a água chega;
- longe de árvores e de onde escorre água do telhado;
- regulagem num valor médio, não no mínimo.

Se não houver lugar seguro, a saída é um "ignorar sensor de chuva" no app, o que muda o contrato.

📐 **Site CLP.** Sensor de chuva na entrada X1 do CLP.

### 5. Caixa d'água de cada casa

Cada casa tem sua própria caixa d'água (ou poço) e sua própria bomba. Uma casa não vê nem
controla a da outra: o broker separa os usuários por site.

🧪 **Hoje, no site ESP: proteção contra falta de água.** Uma boia na caixa faz duas coisas:

- um contato em série com a bobina do contator corta a bomba fisicamente, mesmo se o firmware errar;
- outro contato vai ao GPIO33 do ESP32. Com nível baixo, o ESP32 para tudo, recusa ligar zona
  (`fault_dry`) e avisa o app (`sensors.level = "low"`, `state.fault = "dry"`).

Fio solto lê como falta de água: o erro é sempre para o lado seguro. A boia ainda não foi comprada,
e falta decidir o modelo com dois contatos (ver *Em aberto* em [`ARCHITECTURE.md`](ARCHITECTURE.md)).

💡 **Ideia: ativar, desativar e controlar a caixa.**

- **Ativa / desativada pelo app.** O dono marca a caixa como fora de uso (limpeza, conserto,
  caixa vazia de propósito) e o quadro trata como falta de água: não liga a bomba nem abre zona.
  É o mesmo caminho do `fault_dry`, só que comandado.
- **Nível em porcentagem**, em vez de só `ok`/`low`: sensor ultrassônico à prova d'água
  (JSN-SR04T) na tampa ou transdutor de pressão no fundo.
- **Controlar a entrada de água:** uma solenoide ou bomba de recalque que enche a caixa,
  com boia de nível alto para não transbordar.
- **Mais de uma fonte por casa** (caixa e poço, ou duas caixas): escolher de qual tirar água.

Falta definir: o que "desativada" deve bloquear (só a irrigação ou também o enchimento) e se cada
casa tem só uma caixa.

---

## Projetado

### 6. Pressão

As válvulas solenoides só abrem e fecham: elas não controlam pressão. Quem controla a
pressão é a bomba ou um regulador na linha.

📐 **Site CLP: pressão constante.** O inversor Metaltex IF10 tem PID de pressão para bomba:
um transdutor 4–20mA na tubulação mede a pressão, e o inversor acelera ou desacelera a bomba
para manter o setpoint em bar. O inversor também para por falta de água, por pressão fora da faixa
e por perda do sensor. O ESP32 lê a pressão pelo Modbus e manda para o app em `sensors.pressureKpa`.
Detalhes em [`hardware/metaltex-if10.md`](hardware/metaltex-if10.md).

💡 **Ideia: pressão diferente por zona.** Gotejador e aspersor pedem pressões diferentes.

- **Site CLP:** trocar o setpoint do PID a cada zona (cada zona com sua pressão em bar no
  `set_zone`). Hoje o projeto diz que o ESP32 nunca escreve no inversor; isso teria que passar
  pelo CLP, por Modbus ou pela saída analógica.
- **Site ESP:** a bomba é liga/desliga, então não dá para regular pelo controlador. As opções
  são reguladores de pressão mecânicos por zona ou válvulas com ajuste de vazão (a Rain Bird
  100-**HVF** tem; a 100-HV comprada não).

### 7. Vazão

📐 **Site CLP.** Sensor de vazão por pulso na entrada X0 do CLP. Detecta tubo estourado
(vazão alta) e zona sem água (vazão zero), e totaliza os litros gastos. Vai para o app em
`sensors.flowLpm`. O site ESP não tem sensor de vazão no projeto.

---

## Ideias

### 8. Umidade do solo por canteiro

💡 Medir a umidade de cada canteiro e regar só quando precisa. Cada canteiro pode ter
**N sensores**, porque um canteiro grande seca de forma desigual (sol, sombra, declive).

Regras possíveis:

- pular a zona no ciclo se a umidade estiver acima de um limite;
- regar até atingir uma umidade alvo, com o tempo da zona como teto;
- juntar os N sensores de um canteiro pela média ou pelo **mais seco**, configurável por canteiro.

Hardware a decidir:

- **Sensor:** capacitivo (não o resistivo, que corrói em semanas).
- **Leitura:** o ESP32 tem poucas entradas analógicas livres com Wi-Fi ligado (GPIO34, 35, 36 e 39).
  Para N sensores, um conversor **ADS1115** no barramento I2C que já existe dá 4 canais por módulo
  e até 4 módulos (16 sensores).
- **Distância:** sinal analógico em cabo longo até o quintal pega ruído. Para canteiros longe do
  quadro, sensores RS-485/Modbus ou **nós sem fio** (ESP32 com bateria falando com o quadro por
  ESP-NOW) devem funcionar melhor.

Contrato: um tópico novo, por exemplo `lotus/v1/{site}/zone/{n}/moisture` com a leitura de cada
sensor e o valor agregado, e um `hasMoisture` no `info`.

### 9. Tempo: nublado, ensolarado, previsão

💡 Usar o tempo para ajustar a rega, não só para pular por chuva:

- **ensolarado e quente:** aumentar a duração das zonas;
- **nublado:** reduzir;
- **chuva prevista para as próximas horas:** pular o ciclo antes de chover.

Duas fontes, que podem se somar:

- **Sensor local de luz** (BH1750, I2C) no quadro: mede sol e nuvem no próprio quintal.
- **Previsão do tempo pela internet** (ex.: Open-Meteo, grátis e sem chave). Pode ser consultada
  pelo ESP32 ou pelo app. Se a internet cair, o quadro deve regar normalmente, sem ajuste.

A forma mais simples é um **fator de ajuste** (ex.: 50% a 150%) aplicado à duração de todas as
zonas, publicado em `state` para o app mostrar.

### 10. Canteiros dentro de canteiros (válvulas aninhadas)

💡 Uma válvula principal alimenta um canteiro, e dentro dele outras válvulas dividem em
sub-canteiros. Exemplo: a zona 3 é a horta, e dentro dela há válvulas para alface, tomate e ervas.

```
 Bomba ── Zona 3 (horta) ──┬── 3.1 alface
                           ├── 3.2 tomate
                           └── 3.3 ervas
```

Regras que isso exige:

- um sub-canteiro só abre com a válvula de cima aberta; a de cima abre antes e fecha depois;
- a válvula de cima fica aberta enquanto houver qualquer sub-canteiro regando;
- a duração, a umidade (item 8) e a pressão (item 6) passam a ser por sub-canteiro;
- os níveis podem se repetir (canteiro dentro de sub-canteiro), então o modelo é uma **árvore de zonas**.

Impacto:

- **Saídas:** cada válvula gasta um relé. O site ESP já usa os 8. Mais válvulas pedem outra
  placa de relés ligada por um expansor I2C de saída (PCF8574/MCP23017).
- **Firmware:** o `sprinkler` do ESPHome tem só um nível (válvula + bomba). A árvore teria que ser
  feita à mão no firmware.
- **Contrato:** a zona passa a ter um identificador hierárquico (`3.1`) ou um campo `parent`,
  e o `info` precisa descrever a árvore. Isso muda o `lotus/v1`, então provavelmente vira `lotus/v2`.

---

## Em aberto

- [ ] Caixa "desativada": o que exatamente ela bloqueia, e cada casa tem uma caixa só?
- [ ] Pressão por zona: vale o custo no site ESP ou fica só no site CLP?
- [ ] Umidade: quantos canteiros e sensores por casa, e a que distância do quadro?
- [ ] Previsão do tempo: consultar no ESP32 ou no app?
- [ ] Canteiros aninhados: quantos níveis e quantas válvulas no total por casa?
