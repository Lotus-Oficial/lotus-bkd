# Broker MQTT

O ponto de encontro entre os quadros e o app (veja `docs/ARCHITECTURE.md`, seção 3).
Contrato das mensagens: [`docs/CONTRATO-MQTT.md`](../docs/CONTRATO-MQTT.md).

## Nuvem: EMQX Serverless

Plano gratuito: 1 milhão de minutos de sessão por mês. Um cliente conectado o mês inteiro
gasta ~44 mil, então dois quadros e alguns celulares cabem com folga. TLS na porta 8883.

> O HiveMQ Cloud Serverless, a outra opção da arquitetura, parou de ser vendido em 30/09/2026.

### 1. Criar o deployment

1. Crie a conta em <https://www.emqx.com/en/cloud> e um deployment **Serverless**
   (região mais próxima, ex. `us-east-1`).
2. Em **Overview**, anote o endereço (`xxxxxxxx.ala.us-east-1.emqxsl.com`) e baixe a
   **CA Certificate**. Ela vai para o `mqtt_ca` do `firmware/secrets.yaml`.

### 2. Usuários (Access Control → Authentication)

Um usuário por quadro e um por pessoa. Senhas longas e aleatórias (`openssl rand -base64 24`).

| Usuário | Quem usa |
|---|---|
| `quadro-esp` | ESP32 do site ESP |
| `quadro-clp` | ESP32 do site CLP |
| `app-esp` | app de quem usa o site ESP |
| `app-clp` | app de quem usa o site CLP |
| `app-admin` | app e ferramentas de quem administra as duas casas |

### 3. Regras (Access Control → Authorization)

Por padrão o EMQX libera tudo. As regras abaixo, com o **deny geral por último**,
transformam isso em lista branca: o que não está aqui é negado.

| Usuário | Tópico | Ação | Permissão |
|---|---|---|---|
| `quadro-esp` | `lotus/v1/esp/#` | Publish & Subscribe | Allow |
| `quadro-clp` | `lotus/v1/clp/#` | Publish & Subscribe | Allow |
| `app-esp` | `lotus/v1/esp/#` | Subscribe | Allow |
| `app-esp` | `lotus/v1/esp/cmd` | Publish | Allow |
| `app-clp` | `lotus/v1/clp/#` | Subscribe | Allow |
| `app-clp` | `lotus/v1/clp/cmd` | Publish | Allow |
| `app-admin` | `lotus/v1/#` | Subscribe | Allow |
| `app-admin` | `lotus/v1/+/cmd` | Publish | Allow |
| *All Users* | `#` | Publish & Subscribe | **Deny** |

O resultado: cada casa só vê e comanda a própria árvore; um app não consegue forjar o
estado de um quadro, porque só publica no `cmd`.

### 4. Testar

Crie um `.env` na raiz do repositório (ignorado pelo git):

```sh
LOTUS_MQTT_HOST=xxxxxxxx.ala.us-east-1.emqxsl.com
LOTUS_MQTT_USER=app-admin
LOTUS_MQTT_PASS=...
LOTUS_MQTT_CA=/caminho/para/emqxsl-ca.crt
```

Depois, em terminais separados:

```sh
LOTUS_MQTT_USER=quadro-esp LOTUS_MQTT_PASS=... tools/lotus_mqtt.py simular esp --rapido
tools/lotus_mqtt.py ouvir
tools/lotus_mqtt.py cmd esp start_cycle
```

O `tools/lotus_mqtt.py` roda com o `uv`, que baixa sozinho a dependência (`paho-mqtt`).

## Local: Mosquitto no Docker

Para desenvolver sem internet e sem gastar a cota. Não tem TLS e não serve para o ESP32,
que exige TLS no firmware. As regras de acesso em `local/acl` espelham as da nuvem, e
todos os usuários têm a senha `lotus`.

```sh
docker compose -f broker/local/compose.yaml up -d

export LOTUS_MQTT_HOST=localhost LOTUS_MQTT_TLS=0 LOTUS_MQTT_PASS=lotus
LOTUS_MQTT_USER=quadro-esp tools/lotus_mqtt.py simular esp --rapido &
LOTUS_MQTT_USER=app-esp  tools/lotus_mqtt.py cmd esp start_zone zone=2 durationS=300
```

Para recriar o `local/passwd`:

```sh
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD/broker/local":/w eclipse-mosquitto:2 \
  sh -c 'cd /w && rm -f passwd && touch passwd && for u in quadro-esp quadro-clp app-esp app-clp app-admin; do mosquitto_passwd -b passwd $u lotus; done'
```
