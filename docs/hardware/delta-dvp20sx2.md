# CLP Delta DVP20SX211R (site CLP)

Fonte: `docs/manuais/delta-dvp-sx2-instruction-sheet.pdf` (instruction sheet da série SX2).
O mapa Modbus e os registradores especiais (D1120, M1120, M1143) **não** estão nesse documento.
Eles ficam no *DVP-ES2/EX2/SS2/SA2/SX2 Programming Manual*, que ainda está pendente.

## Dados confirmados no manual

| Item | Valor |
|---|---|
| Alimentação | **24Vdc** (faixa 20,4–28,8V), 4,7W, pico de partida de 7,5A. Abaixo de 20,4V o CLP para e desliga todas as saídas |
| Fonte Delta compatível | DVPPS01 (24V/1A) ou DVPPS02 (24V/2A). Qualquer fonte 24Vdc de trilho serve |
| Entradas X0–X7 | 24Vdc, 5mA, **sink ou source** (comum S/S), filtro de 0–20ms ajustável em D1020 (padrão 10ms). X0 e X2 são rápidas (até 2,5µs), boas para o hidrômetro de pulso |
| Saídas Y0–Y5 | Relé, até 250VAC, **1,5A por ponto, 5A por comum**. C0 = Y0–Y2 e C1 = Y3–Y5. Máximo de 1Hz |
| Entrada analógica | ±10V (>1MΩ) ou ±20mA / **4–20mA (250Ω)**, 12 bits. **Em corrente, é preciso jumpear V+ com I+** |
| Saída analógica | ±10V (carga ≥5kΩ) ou 0/4–20mA (carga ≤500Ω), 12 bits |
| Isolação analógica | **Nenhuma** entre o circuito analógico e o digital |
| RS-485 (COM2) | Bornes **D+, D−, SG**. Resistor de 120Ω no mestre e no último escravo. Cabo de par trançado blindado 20AWG. Ligar o SG entre os equipamentos |
| RTC | Tem relógio. O erro máximo é de cerca de 2 min por mês, e ele se mantém por **uma semana** sem energia (firmware v2.00 ou superior) |
| Ambiente | 0–55°C, 50–95% de umidade sem condensação |

## Consequências para o projeto

- **Laço 4–20mA em série com o inversor:** a entrada do CLP tem 250Ω e o AVI do IF10 também.
  São 500Ω × 20mA = 10V de queda no laço. Um transdutor alimentado por 24V aguenta isso, mas
  confirme no datasheet do transdutor a carga máxima que ele suporta.
- **Válvulas:** solenoides de 24VAC puxam cerca de 0,2–0,4A, muito abaixo de 1,5A por ponto.
- **O relé do CLP aguenta só 1Hz.** Ele não pode fazer PWM nem pulso rápido, o que não é problema para válvulas.
- **Entradas em sink:** o S/S vai no 0V e os contatos secos (botões, boia, sensor de chuva, relé
  RA/RC do inversor, hidrômetro reed) chaveiam +24V na entrada X.
- **A fonte de 24Vdc precisa aguentar o pico de 7,5A** ou ter partida suave. Uma fonte chaveada
  de trilho de 2A atende, porque o pico é muito curto.

## Pendente: confirmar no manual de programação

- Endereços Modbus (X = 0x0400, Y = 0x0500, M = 0x0800, D = 0x1000, escritos de memória).
- Configuração do COM2 para Modbus RTU 8N1 (D1120, M1120, M1143).
- Instrução PID, caso se decida fazer o controle de pressão no CLP em vez do inversor.
