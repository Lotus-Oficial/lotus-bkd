# Inversor Metaltex IF10-203-1 (site CLP)

Fontes: `docs/manuais/metaltex-if10-catalogo.pdf` e `docs/manuais/metaltex-if10-20x-1-manual.pdf`
(Ref. 4-003-1.5, jul/2021). As páginas citadas abaixo são as do manual.

## Dados do equipamento

- Entrada monofásica 220V (L1 e L2), corrente de entrada **16A**. Usar disjuntor de 20A.
- Saída trifásica 0–220V, **11A, 3cv / 2,2kW**.
- Controle escalar V/F, com 150% de torque de partida a 5Hz.
- Bornes de controle:
  - entradas digitais **FWD, REV, S1, S2**;
  - entrada analógica **AVI**, que aceita 0–10V ou 4–20mA conforme a chave seletora I/V
    (em corrente, a impedância é 250Ω);
  - **+10V** de referência;
  - relé **RA/RC** NA, 250VAC/3A;
  - **RS+/RS−** (RS-485).
- Ambiente de -10 a 60°C, sem condensação. Instalar em quadro protegido de líquidos e poeira.

## Recursos que o projeto usa

O IF10 tem um modo pronto de **"abastecimento de água por pressão constante"**, com recursos
específicos para bomba:

| Recurso | Parâmetros | Para que serve |
|---|---|---|
| PID de pressão | P600–P618 | Mantém a pressão no setpoint (em bar) usando o transdutor 4–20mA no AVI |
| Detecção de falta d'água | P641, P644, P646, P647 | Para a bomba se a pressão não sobe (bomba rodando a seco) e tenta religar depois |
| Alarme de pressão alta/baixa | P605, P606, P642, P643 | Para a bomba se a pressão sair da faixa (tubo estourado ou registro fechado) |
| Perda do sensor | P621–P623 | Gera falha 20 se o laço 4–20mA romper (sinal abaixo de 2mA) |
| Repouso (sleep) | P652–P656 | Desacelera e dorme quando não há consumo, mostrando "SLP" no display |
| Relé de saída | P325 | Na fábrica (valor 3) o relé indica **alarme**. Esse contato vai para o X6 do CLP |

## Parametrização proposta

Antes de tudo, rodar **P117 = 8** (volta aos valores de fábrica) e depois desligar e religar o inversor.

| Parâmetro | Valor | Fábrica | Motivo |
|---|---|---|---|
| **P105** | **60.0** | 50.0 | Frequência máxima. A fábrica vem em 50Hz; no Brasil o motor é de 60Hz |
| **P110** | **60.0** | 50.0 | Frequência base da curva V/F |
| P801 | 1 | 1 | Rede de 60Hz |
| P209 / P210 / P212 / P215 | placa do motor | — | Tensão, corrente, rpm e frequência nominais da bomba |
| P107 / P108 | ~3–5s | — | Rampas de aceleração e desaceleração suaves, para evitar golpe de aríete |
| P104 | 0 | 1 | Desabilita a rotação reversa (bomba centrífuga não pode girar ao contrário) |
| P102 | 1 | 0 | Partida e parada pelos terminais (FWD vindo do Y5 do CLP) |
| P103 | 1 | 1 | Mantém o STOP do teclado ativo como parada local |
| P101 | 8 | 3 | Referência de frequência vem do PID |
| P600 | 1 | 0 | PID habilitado |
| P601 | 0 | 0 | Realimentação negativa (pressão baixa faz acelerar) |
| P602 | 0 | 0 | Setpoint vem de P604 |
| P603 | 1 | 0 | Realimentação pelo AVI em corrente. **Chave seletora em I** |
| P614 | fundo de escala do transdutor | 10.00 | Exemplo: transdutor de 0–10 bar dá 10.00 |
| P604 | ~2.0–3.0 bar | 2.50 | Setpoint de pressão. Depende do gotejamento ou dos aspersores |
| P617 / P618 | 60.0 / ~25.0 | 48 / 20 | Faixa de frequência em que o PID atua |
| P621 / P622 / P623 | 2 / 0.50V / 1.0s | 0 / 0.50 / 1.0 | Para a bomba se perder o sensor |
| P641 / P644 | ~0.5 bar / ~30s | 0.50 / 100s | Ajustar a detecção de falta d'água em campo |
| P325 | 3 | 3 | Relé RA/RC sinaliza alarme |

Os ganhos do PID (P607 banda, P608 integral, P609 derivativo) ficam no valor de fábrica e
são afinados no comissionamento.

## Modbus-RTU (manual, seção 7)

**Suporte limitado:** o inversor só aceita leitura (**03/04**) e escrita de um registrador (**06**).
Não aceita coils. O registrador 2000H só pode ser escrito; tentar lê-lo gera erro.

| Parâmetro | Valor para o barramento com o ESP32 |
|---|---|
| P700 | 1 = 9600 bps (mesmo baud rate do CLP) |
| P701 | 3 = 8N1 RTU |
| P702 | **2** (a fábrica vem com **0**, que no Modbus é endereço de broadcast. Precisa mudar) |
| P703 | 0 = sem aviso. O inversor não é comandado por Modbus, então perder a comunicação não deve gerar falha |

| Endereço | Acesso | Conteúdo | Escala |
|---|---|---|---|
| 2000H | escrita | Comando: 1 = parada, 2 = partida, 8 = FWD, 16 = reset de alarme | — |
| 2001H | leitura/escrita | Frequência de comando (só com P101 = 5) | 0,01 Hz |
| 0001H | leitura | Frequência ajustada | 0,01 Hz |
| 0002H | leitura | Frequência de saída | 0,1 Hz |
| 0003H | leitura | Corrente de saída | 0,1 A |
| 0004H | leitura | Velocidade | rpm |
| 0005H | leitura | Tensão do barramento DC | 0,1 V |
| 0009H | leitura | Tensão de saída | 0,1 V |
| 0014H | leitura | Potência (P020) | 0,1 kW |
| 001BH | leitura | Bits de alarme (P027): b0 UC, b1 OC, b2 erro de comunicação, b3 falta de fase, b4 OU, b6 LU, b7 OL, b8 OT, b9 OH, b10 erro no 4mA, b15 alarme geral | bitmask |
| 001CH | leitura | Status (P028): b0 FWD/REV, b1 Stop/Run | bitmask |

**Não documentado, a testar na bancada:** pelo padrão da tabela, o endereço Modbus é o próprio
número do parâmetro (P020 → 0014H, P027 → 001BH). Se isso valer para todos, **0007H** deve
devolver a realimentação do PID (P007, a pressão) e **0006H** a temperatura (P006).

**Uso no projeto:** só **leitura** (telemetria: pressão, corrente, potência, alarmes). Quem comanda
o inversor é o CLP, pela fiação.

## Códigos de falha relevantes (manual, seção 4)

| Código | Significado | Causa provável no contexto de bomba |
|---|---|---|
| OC1–OC3 | Sobrecorrente | Rampa curta, bomba travada, cabo em curto |
| OU1–OU3 | Sobretensão | Desaceleração rápida demais |
| LU0–LU3 | Subtensão | Rede fraca ou queda de tensão na partida |
| OL / OT | Sobrecarga do inversor ou do motor | Bomba subdimensionada ou rotor travado |
| OH | Superaquecimento | Quadro sem ventilação |
| 20 | Laço 4–20mA rompido | Cabo do transdutor solto |
| CO | Erro de comunicação | Fiação RS-485 ou parâmetros P700/P701 |
| SLP | Em repouso | Normal: não há consumo |
