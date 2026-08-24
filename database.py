"""
Camada de banco de dados (SQLite) para o bot.

Guarda:
- tickets: solicitações de funcional (do ticket até a aprovação/recusa)
- advertencias: histórico de advertências aplicadas

Todas as funções aqui são SÍNCRONAS (usam sqlite3 puro, sem dependências
externas). Para não travar o loop de eventos do discord.py, o bot deve
chamá-las sempre através de `asyncio.to_thread(...)` — veja os helpers
async no final do arquivo, prontos para importar direto no bot.py.
"""

import sqlite3
import os
import asyncio
import json
import random
import string
from datetime import datetime, timezone

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "bot_data.db"))

# Prefixo do código de identificação de cada funcional (ex: 9BPM-8K2P4X).
CODIGO_PREFIXO = "9BPM-"
CODIGO_TAMANHO = 6
CODIGO_ALFABETO = string.ascii_uppercase + string.digits


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    """Cria as tabelas caso não existam. Chamar uma vez, antes do bot.run()."""
    conn = _get_conn()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                canal_id        INTEGER,
                status          TEXT NOT NULL DEFAULT 'aberto',
                codigo          TEXT,
                nome            TEXT,
                passaporte      TEXT,
                cia             TEXT,
                cargo_cia_id    INTEGER,
                patente_nome    TEXT,
                patente_roles   TEXT,
                log_channel_id  INTEGER,
                log_message_id  INTEGER,
                aprovado_por    INTEGER,
                criado_em       TEXT NOT NULL,
                atualizado_em   TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS advertencias (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                aplicado_por  INTEGER NOT NULL,
                motivo        TEXT,
                nivel         INTEGER NOT NULL,
                criado_em     TEXT NOT NULL
            )
            """
        )

        # --- migração: bancos criados antes da coluna 'codigo' existir ---
        # ALTER TABLE ADD COLUMN não suporta "IF NOT EXISTS" no SQLite,
        # então tentamos e ignoramos o erro se a coluna já existir.
        try:
            conn.execute("ALTER TABLE tickets ADD COLUMN codigo TEXT")
        except sqlite3.OperationalError:
            pass  # coluna já existe

        # índices que a gente realmente consulta
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tickets_user_status ON tickets(user_id, status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tickets_log_message ON tickets(log_message_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tickets_canal ON tickets(canal_id)")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tickets_codigo ON tickets(codigo)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_adv_user ON advertencias(user_id)")
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CÓDIGO ÚNICO DE IDENTIFICAÇÃO
# ---------------------------------------------------------------------------

def _codigo_existe(conn: sqlite3.Connection, codigo: str) -> bool:
    row = conn.execute("SELECT 1 FROM tickets WHERE codigo = ? LIMIT 1", (codigo,)).fetchone()
    return row is not None


def _gerar_codigo_unico(conn: sqlite3.Connection) -> str:
    """Gera um código tipo 9BPM-8K2P4X garantindo que não colide com nenhum já salvo."""
    for _ in range(50):  # tentativas de sobra antes de desistir
        sufixo = "".join(random.choices(CODIGO_ALFABETO, k=CODIGO_TAMANHO))
        codigo = f"{CODIGO_PREFIXO}{sufixo}"
        if not _codigo_existe(conn, codigo):
            return codigo
    # extremamente improvável de chegar aqui, mas por segurança:
    raise RuntimeError("Não foi possível gerar um código único para o ticket.")


# ---------------------------------------------------------------------------
# TICKETS / FUNCIONAIS
# ---------------------------------------------------------------------------

def criar_ticket(user_id: int, canal_id: int) -> dict:
    """
    Cria a linha do ticket assim que o canal é aberto, já com um código
    único de identificação. Retorna {"id": <int>, "codigo": <str>}.
    """
    conn = _get_conn()
    try:
        codigo = _gerar_codigo_unico(conn)
        cur = conn.execute(
            "INSERT INTO tickets (user_id, canal_id, status, codigo, criado_em, atualizado_em) "
            "VALUES (?, ?, 'aberto', ?, ?, ?)",
            (user_id, canal_id, codigo, _now(), _now()),
        )
        conn.commit()
        return {"id": cur.lastrowid, "codigo": codigo}
    finally:
        conn.close()


def ticket_aberto_existe(user_id: int) -> bool:
    """
    True se o usuário já tem um ticket em andamento (aberto ou aguardando
    aprovação). Assim que a solicitação é aprovada OU recusada, o status
    muda e essa função volta a retornar False — liberando o botão
    "Solicitar Funcional" automaticamente para ele tentar de novo.
    """
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT id FROM tickets WHERE user_id = ? AND status IN ('aberto', 'aguardando_aprovacao') LIMIT 1",
            (user_id,),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def salvar_dados_pessoais(ticket_id: int, nome: str, passaporte: str, cia: str,
                           cargo_cia_id: int, patente_nome: str, patente_roles: list) -> None:
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE tickets SET nome=?, passaporte=?, cia=?, cargo_cia_id=?, "
            "patente_nome=?, patente_roles=?, atualizado_em=? WHERE id=?",
            (nome, passaporte, cia, cargo_cia_id, patente_nome,
             json.dumps(patente_roles), _now(), ticket_id),
        )
        conn.commit()
    finally:
        conn.close()


def registrar_mensagem_log(ticket_id: int, log_channel_id: int, log_message_id: int) -> None:
    """Marca o ticket como 'aguardando_aprovacao' e guarda onde está o embed de aprovação."""
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE tickets SET status='aguardando_aprovacao', log_channel_id=?, "
            "log_message_id=?, atualizado_em=? WHERE id=?",
            (log_channel_id, log_message_id, _now(), ticket_id),
        )
        conn.commit()
    finally:
        conn.close()


def buscar_ticket_por_log_message(log_message_id: int) -> dict | None:
    """Usado pelos botões Aceitar/Recusar: acham o ticket pela mensagem em que foram clicados."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM tickets WHERE log_message_id = ?", (log_message_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def buscar_ticket_por_codigo(codigo: str) -> dict | None:
    """
    Fallback: localiza o ticket pelo código único (ex: FT-8K2P4X) em vez do
    ID da mensagem de log. Útil se a mensagem de aprovação for apagada,
    editada manualmente ou perdida por qualquer motivo — as informações
    da solicitação não se perdem, pois continuam associadas ao código.
    """
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM tickets WHERE codigo = ?", (codigo.strip().upper(),)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def buscar_ticket_por_canal(canal_id: int) -> dict | None:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM tickets WHERE canal_id = ?", (canal_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def finalizar_ticket(ticket_id: int, status: str, aprovado_por: int | None = None) -> None:
    """status: 'aprovado' ou 'recusado'."""
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE tickets SET status=?, aprovado_por=?, atualizado_em=? WHERE id=?",
            (status, aprovado_por, _now(), ticket_id),
        )
        conn.commit()
    finally:
        conn.close()


def listar_tickets(status: str | None = None, limite: int = 50) -> list[dict]:
    conn = _get_conn()
    try:
        if status:
            rows = conn.execute(
                "SELECT * FROM tickets WHERE status=? ORDER BY criado_em DESC LIMIT ?",
                (status, limite),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tickets ORDER BY criado_em DESC LIMIT ?", (limite,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# ADVERTÊNCIAS
# ---------------------------------------------------------------------------

def aplicar_advertencia(user_id: int, aplicado_por: int, motivo: str, nivel: int) -> None:
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO advertencias (user_id, aplicado_por, motivo, nivel, criado_em) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, aplicado_por, motivo, nivel, _now()),
        )
        conn.commit()
    finally:
        conn.close()


def historico_advertencias(user_id: int) -> list[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM advertencias WHERE user_id = ? ORDER BY criado_em DESC", (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def remover_ultima_advertencia(user_id: int) -> dict | None:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM advertencias WHERE user_id = ? ORDER BY criado_em DESC, id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        if not row:
            return None
        registro = dict(row)
        conn.execute("DELETE FROM advertencias WHERE id = ?", (registro["id"],))
        conn.commit()
        return registro
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# WRAPPERS ASSÍNCRONOS
# Use estes dentro do bot.py — eles rodam a chamada síncrona numa thread
# separada para não travar o loop de eventos do discord.py.
# ---------------------------------------------------------------------------

async def a_criar_ticket(user_id: int, canal_id: int) -> dict:
    return await asyncio.to_thread(criar_ticket, user_id, canal_id)


async def a_ticket_aberto_existe(user_id: int) -> bool:
    return await asyncio.to_thread(ticket_aberto_existe, user_id)


async def a_salvar_dados_pessoais(*args, **kwargs) -> None:
    return await asyncio.to_thread(salvar_dados_pessoais, *args, **kwargs)


async def a_registrar_mensagem_log(*args, **kwargs) -> None:
    return await asyncio.to_thread(registrar_mensagem_log, *args, **kwargs)


async def a_buscar_ticket_por_log_message(log_message_id: int) -> dict | None:
    return await asyncio.to_thread(buscar_ticket_por_log_message, log_message_id)


async def a_buscar_ticket_por_codigo(codigo: str) -> dict | None:
    return await asyncio.to_thread(buscar_ticket_por_codigo, codigo)


async def a_finalizar_ticket(*args, **kwargs) -> None:
    return await asyncio.to_thread(finalizar_ticket, *args, **kwargs)


async def a_aplicar_advertencia(*args, **kwargs) -> None:
    return await asyncio.to_thread(aplicar_advertencia, *args, **kwargs)


async def a_historico_advertencias(user_id: int) -> list[dict]:
    return await asyncio.to_thread(historico_advertencias, user_id)


async def a_remover_ultima_advertencia(user_id: int) -> dict | None:
    return await asyncio.to_thread(remover_ultima_advertencia, user_id)