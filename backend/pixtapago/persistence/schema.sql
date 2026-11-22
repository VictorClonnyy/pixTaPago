CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS charges (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  txid TEXT NOT NULL UNIQUE,
  payer_name TEXT NOT NULL,
  amount NUMERIC NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL,
  pix_copy_paste TEXT NOT NULL,
  location TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS receipts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  e2eid TEXT NOT NULL UNIQUE,
  txid TEXT,
  payer_name TEXT NOT NULL,
  amount NUMERIC NOT NULL,
  origin TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  received_at TEXT NOT NULL,
  FOREIGN KEY (txid) REFERENCES charges(txid)
);

CREATE TABLE IF NOT EXISTS bank_accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  document TEXT NOT NULL,
  pix_key TEXT NOT NULL UNIQUE,
  balance_cents INTEGER NOT NULL CHECK (balance_cents >= 0),
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bank_transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  e2eid TEXT NOT NULL UNIQUE,
  idempotency_key TEXT NOT NULL UNIQUE,
  sender_id INTEGER NOT NULL,
  receiver_id INTEGER NOT NULL,
  amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
  description TEXT NOT NULL DEFAULT '',
  payment_method TEXT NOT NULL,
  txid TEXT NOT NULL DEFAULT '***',
  created_at TEXT NOT NULL,
  FOREIGN KEY (sender_id) REFERENCES bank_accounts(id),
  FOREIGN KEY (receiver_id) REFERENCES bank_accounts(id)
);

CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  receipt_e2eid TEXT NOT NULL UNIQUE,
  message TEXT NOT NULL,
  created_at TEXT NOT NULL,
  read_at TEXT,
  FOREIGN KEY (receipt_e2eid) REFERENCES receipts(e2eid)
);
