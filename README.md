# PixTáPago

Protótipo web para criação e confirmação de cobranças Pix, baseado nos requisitos e nas telas do projeto. O backend Flask mantém autenticação, cobranças, recebimentos e webhook; o frontend React + TypeScript reproduz os cinco fluxos definidos no documento.

## Stack

- Backend: Python, Flask, SQLite e adaptador para API Pix v2 do Banco do Brasil
- Frontend: React, TypeScript, Vite e QR Code renderizado no navegador
- Integração: sandbox/homologação da API Pix v2 do Banco do Brasil

## Execução rápida (Windows)

Dê dois cliques em **`Rodar PixTaPago.bat`**, na raiz do projeto. O script:

1. verifica se Python e Node.js/npm estão no PATH;
2. cria `backend/.venv` e instala o `requirements.txt` (de novo só quando o arquivo muda);
3. cria `backend/.env` a partir do `.env.example`, caso ainda não exista;
4. roda `npm install` no frontend na primeira vez;
5. abre duas janelas, **Backend (Flask :5000)** e **Frontend (Vite :5173)**;
6. espera o frontend responder e abre `http://localhost:5173` no navegador.

Para parar, feche as duas janelas.

## Guias disponíveis

### Painel do estabelecimento (exige login)

| Guia | Endereço | O que faz |
|---|---|---|
| Login | `http://localhost:5173/` | Tela de acesso (UC007). Usuário `demo@pixtapago.com.br`, senha `pix123` |
| Dashboard | `http://localhost:5173/` | Resumo de cobranças e recebimentos (UC008) |
| Cobranças | `http://localhost:5173/charges` | Lista as cobranças criadas e o status de cada uma |
| Gerar cobrança | `http://localhost:5173/charges/new` | Cria uma cobrança imediata com QR Code e Copia e Cola (UC002) |
| Detalhes da cobrança | `http://localhost:5173/charges/{txid}` | Consulta o status de uma cobrança pelo TXID (UC003) |
| Recebimentos | `http://localhost:5173/receipts` | Histórico com busca e filtro por período (UC005) |
| Notificações | sino no cabeçalho | Avisos de Pix recebido, com "marcar como lida" (UC006) |

### Simulador bancário (sem login)

| Guia | Endereço | Conta |
|---|---|---|
| Cliente | `http://localhost:5173/cliente` | Pedro, o pagador. Tem **Transferir Pix** (por chave) e **Pagar QR Code** (câmera ou Copia e Cola) |
| Dono | `http://localhost:5173/dono` | João, o recebedor. Mostra saldo e extrato da chave `BB_PIX_KEY` |

### Portas

| Serviço | Endereço |
|---|---|
| Frontend (Vite) | `http://localhost:5173` |
| Backend (Flask) | `http://localhost:5000`, com a API em `/api` (o Vite repassa `/api` para cá) |

## Executar no sandbox local (manual)

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

### Frontend

Em outro terminal:

```powershell
cd frontend
npm install
npm run dev
```

Acesse `http://localhost:5173`.

- Usuário: `demo@pixtapago.com.br`
- Senha: `pix123`

### Experiência bancária

As duas contas usam a mesma interface e mantêm saldo e movimentações sincronizados:

- Pedro (cliente): `http://localhost:5173/cliente` — chave Pix `pedro@bancoaurora.com.br`
- João (responsável pelo estabelecimento): `http://localhost:5173/dono` — usa a chave configurada em `BB_PIX_KEY` (`hmtestes2@bb.com.br` na homologação)

Na conta do Pedro, use **Transferir Pix** para pagar pela chave do João ou **Pagar QR Code**
para abrir a câmera e ler o QR Code de uma cobrança. O Pix Copia e Cola continua disponível
como alternativa. A liquidação debita e credita as contas na mesma transação, gera um
identificador E2E, protege reenvios por chave de idempotência e atualiza os extratos
automaticamente. O recebedor visualiza o nome do pagador.

As rotas `/cliente` e `/dono` representam a experiência bancária do protótipo e movimentam
somente as contas locais. Elas não são uma API pagadora do BB. Para validar a integração oficial,
o pagamento deve ser efetuado pelo recurso de teste do Portal/Swagger do BB; o PixTáPago confirma
o resultado por `GET /pix`, `GET /cob/{txid}` ou pelo webhook.

O acesso à câmera funciona em `localhost` durante o desenvolvimento e exige HTTPS quando a
aplicação for publicada. O leitor aceita QR Code estático e o QR dinâmico correspondente a uma
cobrança criada pelo PixTáPago com o payload devolvido pela API do BB.

## Arquitetura do backend

O backend segue uma arquitetura em camadas, com dependências sempre no sentido
apresentação → aplicação → domínio, e com persistência e integração isoladas:

```text
backend/
├── app.py                         ponto de entrada (create_app)
├── pixtapago/
│   ├── __init__.py                fábrica da aplicação Flask e registro dos blueprints
│   ├── config.py                  configuração lida do .env
│   ├── api/                       apresentação REST
│   │   ├── auth_routes.py         UC007/UC001 login, logout, sessão
│   │   ├── charge_routes.py       UC002/UC003/UC008 cobranças e painel
│   │   ├── receipt_routes.py      UC004 webhook e sincronização, UC005 histórico, UC006 notificações
│   │   ├── security.py            exigência de sessão e comparação segura de segredo
│   │   └── dependencies.py        composição dos serviços por requisição
│   ├── services/                  aplicação (um serviço por grupo de casos de uso)
│   │   ├── auth_service.py
│   │   ├── charge_service.py
│   │   ├── payment_confirmation_service.py
│   │   ├── notification_service.py
│   │   └── receipt_history_service.py
│   ├── domain/                    entidades, objetos de valor, erros e payload EMV
│   ├── persistence/               SQLite: database.py, schema.sql, repositories.py
│   ├── integration/               cliente da API Pix v2 do Banco do Brasil
│   └── simulator/                 simulador do PSP pagador (/cliente e /dono)
└── tests/                         testes da API, das regras documentadas e do cliente BB
```

O simulador fica fora do escopo funcional do produto: ele representa o banco do pagador
e entrega cada Pix liquidado ao mesmo serviço que trata o webhook do BB.

## API do Banco do Brasil a selecionar

Para o escopo atual, selecione somente **API Pix v2** na aplicação do Portal Developers BB. Ela cobre:

- criação de cobrança imediata (`cob.write`);
- consulta da cobrança por TXID (`cob.read`);
- consulta de Pix recebidos (`pix.read`);
- configuração e consulta de webhook da chave Pix (`webhook.write` e `webhook.read`).

Não selecione **Arrecadação Integrada ao Pix** apenas para ter QR Code. Essa API atende convênios e guias de arrecadação (tributos, taxas, faturas conveniadas), com contratação e conciliação próprias. Ela só deve entrar se o produto evoluir para esse cenário institucional.

## Ligar ao sandbox BB

1. Copie `backend/.env.example` para `backend/.env`.
2. Altere `BB_PIX_MODE=bb`.
3. Preencha Client ID, Client Secret e App Key gerados pelo Portal.
4. Para reproduzir o Swagger de homologação da API Pix v2, use `BB_PIX_KEY=hmtestes2@bb.com.br` e `BB_PIX_BASE_URL=https://api.hm.bb.com.br/pix/v2`.
5. Cadastre um endpoint HTTPS público apontando para `POST /api/webhooks/bb/pix?token=<BB_WEBHOOK_SECRET>` quando testar webhook. `localhost` não recebe chamadas externas. Sem `BB_WEBHOOK_SECRET` configurado, o webhook recusa todas as chamadas (RNF004).

Enquanto a aplicação estiver em `localhost`, o frontend chama `POST /api/pix/sync` a cada cinco
segundos. O backend consulta oficialmente `GET /pix` para capturar qualquer crédito na chave e
`GET /cob/{txid}` para reconciliar cobranças pendentes. Em um servidor público, prefira o webhook
como confirmação imediata e mantenha a consulta periódica como contingência.

O host `api.hm.bb.com.br` usado pelo Swagger de homologação não utiliza o certificado cliente
da aplicação. O host mTLS/produção é uma configuração separada: quando migrar, cadastre a parte
pública do certificado no Portal e configure `BB_MTLS_CERT_PATH` e `BB_MTLS_KEY_PATH`; nunca
versione a chave privada.

O arquivo `backend/pixtapago/integration/bb_pix_client.py` isola a integração bancária. Confirme no Portal os nomes dos campos, scopes e URLs da versão liberada para sua aplicação antes de mudar para produção.

O Copia e Cola não é montado pelo frontend: `backend/pixtapago/integration/bb_pix_client.py` envia `PUT /cob/{txid}` ao BB,
recupera `pixCopiaECola` da resposta e o sistema preserva esse conteúdo para renderizar o QR Code.
A API Pix v2 é uma API do lado recebedor. Em produção, a ordem de pagamento é executada pelo
PSP do pagador; a aplicação do estabelecimento confirma o crédito por webhook ou por consulta da
cobrança no BB.

## Endpoints do protótipo

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /api/dashboard`
- `GET|POST /api/charges`
- `GET /api/charges/{txid}`
- `GET /api/receipts?q=&inicio=AAAA-MM-DD&fim=AAAA-MM-DD`
- `GET /api/notifications?unread=1`
- `POST /api/notifications/{id}/read`
- `POST /api/notifications/read-all`
- `POST /api/pix/sync`
- `POST /api/webhooks/bb/pix`
- `GET /api/bank/accounts/{cliente|dono}`
- `GET /api/bank/pix/resolve?key={chave}`
- `POST /api/bank/pix/preview`
- `POST /api/bank/accounts/{cliente|dono}/pix/transfer`
- `POST /api/bank/accounts/{cliente|dono}/pix/pay`

## Testes

```powershell
cd backend
python -m unittest -v

cd ..\frontend
npm run build
```
