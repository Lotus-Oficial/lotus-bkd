# Manuais de fabricante

Cópias originais dos PDFs. Ao lado de cada um há uma extração em `.txt` (gerada com
`pdftotext -layout`) para facilitar a busca com grep. As notas de projeto
(o que usamos e como configuramos) ficam em `docs/hardware/`.

| Arquivo | Equipamento | Site | Conteúdo | Nota de projeto |
|---|---|---|---|---|
| `metaltex-if10-catalogo.pdf` | Inversor Metaltex IF10 | B | Catálogo: especificações, modelos, dimensões, diagrama básico | [metaltex-if10.md](../hardware/metaltex-if10.md) |
| `metaltex-if10-20x-1-manual.pdf` | Inversor Metaltex IF10-20x-1 | B | Manual de operação Ref. 4-003-1.5 (jul/2021): parâmetros, PID, falhas, Modbus-RTU | [metaltex-if10.md](../hardware/metaltex-if10.md) |
| `delta-dvp-sx2-instruction-sheet.pdf` | CLP Delta DVP20SX211R | B | Instruction sheet: especificações elétricas, E/S, analógicas, ligação, RS-485, RTC | [delta-dvp20sx2.md](../hardware/delta-dvp20sx2.md) |

## Pendentes

- [ ] **Delta DVP-ES2/EX2/SS2/SA2/SX2 Programming Manual**: instruções, registradores especiais
      (D1120/M1120/M1143) e mapa Modbus. Disponível em downloadcenter.deltaww.com.
- [ ] Datasheet das válvulas solenoides, quando forem escolhidas.
- [ ] Datasheet das bombas (site A e site B), quando forem escolhidas.
- [ ] Datasheet do transdutor de pressão 4–20mA (site B).
