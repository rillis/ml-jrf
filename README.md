# ml-jrf

Recebe as notificações (webhooks) do Mercado Livre em `https://api1.rillis.com.br` (porta 52003, via cloudflared) e manda alertas para o Discord: vendas, mensagens, perguntas e reclamações.

## Como funciona

1. **web** (gunicorn, `app/web.py`): valida o JSON e se `user_id`/`application_id` são da conta, grava o bruto em `posts`, enfileira em `webhook_queue` e responde **200 na hora**. Tópicos ignorados (`items`, `claims_actions`) e notificações de outra conta também recebem 200, para o ML não reenviar. Só corpo inválido recebe 400, e só fila fora do ar recebe 503 (o ML reenvia).
2. **worker** (`app/worker.py`): pega os pendentes, consulta a API do ML, envia ao Discord e só então marca como `done`. Depois grava o histórico (`orders_v2`, `messages`, `questions`, `post_purchase`).
   - Falhou? Tenta de novo em 30s, 2min, 10min, 30min e 1h. Se todas falharem, o job vira `failed` e sai um aviso no webhook de debug.
   - Deduplicação: `dedup_key` UNIQUE (o `resource`). Pedidos, mensagens e perguntas alertam uma vez só. Reclamações voltam para a fila a cada notificação e só alertam quando o número de mensagens muda (`alert_key`).
3. Os dois processos rodam no mesmo container (`entrypoint.sh`). Se um morrer, o container sai e o Docker reinicia. Um vigia no `entrypoint.sh` também derruba o container se o worker ficar mais de 10 min sem heartbeat (`WATCHDOG_MAX_AGE`), porque o Docker não reinicia container só por estar `unhealthy`.
4. `GET /health` mostra a fila (pendentes, falhas, atrasados), o heartbeat do worker e se o token está OK. Fica `503` se o banco cair, o worker parar, a fila atrasar mais de 5 min ou o token for recusado.

## Token do ML recusado

Se o ML recusar o refresh token (revogado ou expirado), a fila **pausa**: as notificações ficam guardadas, sem gastar tentativas. Sai **um** aviso no canal de debug com o passo a passo, e outro quando voltar. Para reautorizar:

```bash
docker exec ml-jrf python -m scripts.authorize --url            # mostra a URL de autorização
docker exec ml-jrf python -m scripts.authorize --code <code> --redirect-uri <uri do app>
```

Com `ML_REDIRECT_URI` no `.env`, o `--redirect-uri` pode ser omitido. O worker retoma sozinho em até 5 min.

## Deploy

```bash
cp .env.example .env   # e preencha
mkdir -p data logs && cp <tokens.json atual> data/tokens.json
docker compose run --rm ml-jrf python -m scripts.migrate     # cria a tabela (idempotente)
docker compose up -d --build
docker logs -f ml-jrf
```

O código vai dentro da imagem: depois de qualquer alteração, rode `docker compose up -d --build`. Só `data/` (tokens.json) e `logs/` (security.log, com rotação de 5 MB x 3) são montados.

## Testes

```bash
docker run --rm -u 1000 -v "$PWD":/src -w /src ml-jrf:latest sh -c "pip install -q --user -r requirements-dev.txt && python -m pytest -q -p no:cacheprovider"
```

As fixtures em `tests/fixtures` são respostas reais da API do ML, recortadas e anonimizadas.

## Testar com uma notificação manual

O payload precisa ter o `user_id` e o `application_id` da conta. Com `"debug": true`, a deduplicação é ignorada e nada é gravado em `posts`:

```bash
curl -X POST https://api1.rillis.com.br/ -H 'Content-Type: application/json' \
  -d '{"topic":"orders_v2","resource":"/orders/<id>","user_id":<SELLER_ID>,"application_id":<APP_ID>,"debug":true}'
```

## Consultas úteis

```sql
SELECT status, COUNT(*) FROM webhook_queue GROUP BY status;
SELECT id, topic, dedup_key, attempts, last_error FROM webhook_queue WHERE status IN ('failed','pending') ORDER BY id DESC;
-- reprocessar um job que falhou
UPDATE webhook_queue SET status='pending', attempts=0, next_attempt_at=NOW() WHERE id=<id>;
```

## Ensaio

Com `ENSAIO=1`, a instância usa a tabela `webhook_queue_ensaio`, não grava `posts` nem histórico e não menciona cargos. Use apontando `DISCORD_WEBHOOK_URL` para o webhook de debug. Para reenviar notificações reais: `python -m scripts.replay --url http://127.0.0.1:8000/`.
