import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput
from discord import Embed
import asyncio
import aiohttp
import io
import os
import json
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

import database as db

load_dotenv()

# ============================
#   CONFIGURAÇÕES DO SERVIDOR
# ============================
GUILD_ID = 1343398652336537654

VERIFY_CHANNEL_ID = 0  # Canal de verificação

ROLE_VERIFY_ID = 1343645401051431017  # Cargo de verificado (CARGO: POLICIA MILITAR)
ROLE_AUTOROLE_ID = 1345435302285545652  # Cargo de novato (CARGO: SEM SET)
ADMIN_ROLE_ID = 1449998328334123208  # Cargo de administrador (CARGO: P/1)

PAINEL_CHANNEL_ID = 0  # Canal do painel administrativo

# ============================
#   CANAIS DE LOG (1 por ação)
# ============================
# Cada comando/ação tem seu próprio canal de log.
#
# Como pegar o ID de um canal: Discord > Configurações > Avançado >
# ativar "Modo desenvolvedor" > clique com o botão direito no canal >
# "Copiar ID do Canal".
LOG_CHANNEL_SISTEMA = 1450001931278745640
LOG_CHANNEL_CLEARALL = 1540760853236813825
LOG_CHANNEL_ADV = 1475227661507891270
LOG_CHANNEL_BAN = 1343398653301358625
LOG_CHANNEL_MENSAGEM = 1540762061338845235
LOG_CHANNEL_FUNCIONAL_APROVADO = 1540761917638058015
LOG_CHANNEL_FUNCIONAL_RECUSADO = 1540761917638058015
LOG_CHANNEL_INSCRICOES = 1480372275575525517
INSCRICOES_DB_PATH = os.path.join(os.path.dirname(__file__), "inscricoes.json")

# Advertências
ID_CARGO_ADV1 = 1343788657760534619
ID_CARGO_ADV2 = 1343647931743469620
ID_CARGO_ADV3 = 1343648148861489247
ID_CARGO_AFASTADO = 1343645850294947860

# Autorizados para comandos (todos os slash commands + botões de aprovação usam estes cargos)
CARGOS_AUTORIZADOS = [
    1469854597802754058,  # VUNESP
]
ROLE_INSTRUTOR_ID = 1343646363006668911
ROLE_ADMIN_FUNCIONAL_ID = 1449998328334123208

# ============================
#         SISTEMA DE CURSOS
# ============================
CANAL_PAINEL_CURSOS = 1475911649151025325
CANAL_CANDIDATOS_CURSOS = 1475935737215193280
CANAL_LOGS_CURSOS = 1540946606038188114
CANAL_CONTROLE_CURSOS = 1476076702777081857
CANAL_CERTIFICADOS = 1476077153547325440
CARGOS_INSTRUTOR = [1343646363006668911]
CURSOS_DB_PATH = os.path.join(os.path.dirname(__file__), "sistema_rota.db")
BANNER_CURSO = "https://cdn.discordapp.com/attachments/1444735189765849320/1540875386370654339/9_bpm_CERTIFICADOS_.png?ex=6a8b8b88&is=6a8a3a08&hm=30cb17163b540766a63085d6b5dd4b6e08bac133a273dd2bb9595ce8cb4f2511&"
BANNER_CERTIFICADO = "https://cdn.discordapp.com/attachments/1444735189765849320/1540874527670800455/DIPLONA_9BPM.png?ex=6a8b8abb&is=6a8a393b&hm=15445fe302f40d3137131451da853ab12b22a8e0929702f0a7a026d2e8deb6c3&"
CURSOS_DISPONIVEIS = [
    "Curso Op. Especial", "Curso Superior de Polícia Militar", "Curso de Aperfeiçoamento de Oficiais",
    "Curso de Formação de Oficiais", "Curso de Formação de Sargentos", "Curso de Formação de Cabos",
    "Curso de Formação de Soldados", "Curso de P.O.P", "Curso de Abordagem e Posicionamento",
    "Curso de Modulação", "Curso de Confecção de BOPM", "Curso de TAT I", "Curso de TAT II",
    "Curso de TAT III", "SAT A", "SAT B",
]

# ============================
#         CARGOS AURORIZADOS USAR COMANDOS / 
# ============================
ROLE_VUNESP_ID = 1469854597802754058
ROLE_INSTRUTOR_ID = 1343646363006668911
ROLE_P1_ID = 1449998328334123208

# ============================
#       SISTEMA DE AUSÊNCIA
# ============================
CANAL_AUSENCIA_ID = 1449997864255357091
LOG_AUSENCIA_ID = 1449997591713677362
IMAGEM_AUSENCIA_URL = "https://cdn.discordapp.com/attachments/1444735189765849320/1541258863842427031/9_bpm_INSCRICOES_1.png?ex=6a8cf0ac&is=6a8b9f2c&hm=383831dac53fba8a329ad50147a4f85ab2806425e3f539750ffa8814196585fa&"

# ==========================
#       SISTEMA DE BOLETIM
# ==========================
ID_CANAL_BOLETIM = 1449997658935525457
ID_CATEGORIA_TICKETS_BOLETIM = 1475279716293283861
ID_CARGO_GERAL_BOLETIM = 1449985109116715008
ID_CARGO_VUNESP_BOLETIM = 1541511597577601136
ID_CARGO_P1_BOLETIM = 1449998328334123208
CANAL_BOLETINS = {
    "9°BPM": 1450996140043538573,
}
CARGOS_AUTORIZADOS_BOLETIM = {
    ID_CARGO_VUNESP_BOLETIM: "VUNESP",
    ID_CARGO_P1_BOLETIM: "P/1",
    ID_CARGO_GERAL_BOLETIM: "Geral",
}
RASCUNHO_EXPIRACAO_HORAS = 24



def cursos_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(CURSOS_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def iniciar_db_cursos() -> None:
    with cursos_conn() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS cursos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, data TEXT, horario TEXT, local TEXT, vagas INTEGER, instrutor_id INTEGER, msg_id INTEGER, canal_id INTEGER, status TEXT DEFAULT 'ABERTO')")
        conn.execute("CREATE TABLE IF NOT EXISTS inscritos (curso_id INTEGER, user_id INTEGER, tipo TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, UNIQUE(curso_id, user_id))")
        conn.execute("CREATE TABLE IF NOT EXISTS config (chave TEXT PRIMARY KEY, valor INTEGER)")
        conn.execute("INSERT OR IGNORE INTO config (chave, valor) VALUES ('cert_count', 0)")


def eh_instrutor(member: discord.Member) -> bool:
    return any(role.id in CARGOS_INSTRUTOR for role in getattr(member, "roles", []))


def estilo_curso(embed: discord.Embed) -> discord.Embed:
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8c9598&is=6a8b4418&hm=0b9faa95c5cc5c9231eb5090e3ba60d87bbcf067a833b9fe9c655d32bc737a87&")
    embed.set_footer(text="Batalhão 9° BPM/M Virtual® Todos direitos reservados", icon_url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8c9598&is=6a8b4418&hm=0b9faa95c5cc5c9231eb5090e3ba60d87bbcf067a833b9fe9c655d32bc737a87&")
    return embed


async def log_curso(titulo: str, descricao: str, cor: discord.Color = discord.Color.yellow()):
    canal = bot.get_channel(CANAL_LOGS_CURSOS)
    if canal:
        await canal.send(embed=estilo_curso(discord.Embed(title=titulo, description=descricao, color=cor)))


async def atualizar_curso(curso_id: int, mensagem: discord.Message | None = None):
    with cursos_conn() as conn:
        curso = conn.execute("SELECT * FROM cursos WHERE id=?", (curso_id,)).fetchone()
        alunos = conn.execute("SELECT user_id FROM inscritos WHERE curso_id=? AND tipo='ALUNO' ORDER BY timestamp", (curso_id,)).fetchall()
        fila = conn.execute("SELECT user_id FROM inscritos WHERE curso_id=? AND tipo='FILA' ORDER BY timestamp", (curso_id,)).fetchall()
    if not curso:
        return
    limite = curso["vagas"] or 0
    status = "🔴 CURSO FINALIZADO" if curso["status"] == "FINALIZADO" else ("🟢 INSCRIÇÕES ABERTAS" if not limite or len(alunos) < limite else "🟡 EM FILA DE ESPERA")
    embed = discord.Embed(title=f"`{curso['nome']}`", description=f"**Status:** `{status}`", color=0x2F3136)
    embed.add_field(name="Data:", value=f"`{curso['data']}`", inline=True)
    embed.add_field(name="Horário:", value=f"`{curso['horario']}`", inline=True)
    embed.add_field(name="Local:", value=f"`{curso['local']}`", inline=True)
    embed.add_field(name=f"Inscritos: ({len(alunos)}/{limite or 'Ilimitado'})", value="\n".join(f"<@{row['user_id']}>" for row in alunos) or "_Nenhum inscrito_", inline=False)
    embed.add_field(name=f"Fila de Espera: ({len(fila)})", value="\n".join(f"<@{row['user_id']}>" for row in fila) or "_Vazia_", inline=False)
    embed.set_image(url=BANNER_CURSO)
    estilo_curso(embed)
    if mensagem is None:
        canal = bot.get_channel(curso["canal_id"])
        if canal:
            try:
                mensagem = await canal.fetch_message(curso["msg_id"])
            except discord.HTTPException:
                return
    if mensagem:
        await mensagem.edit(embed=embed, view=None if curso["status"] == "FINALIZADO" else CursoInscricaoView(curso_id))


class CursoInscricaoView(View):
    def __init__(self, curso_id: int):
        super().__init__(timeout=None)
        self.curso_id = curso_id
        inscrever = Button(label="INSCREVER-SE", style=discord.ButtonStyle.secondary, custom_id=f"curso_inscrever:{curso_id}")
        cancelar = Button(label="CANCELAR", style=discord.ButtonStyle.secondary, custom_id=f"curso_cancelar:{curso_id}")
        inscrever.callback = self.inscrever
        cancelar.callback = self.cancelar
        self.add_item(inscrever)
        self.add_item(cancelar)

    async def inscrever(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        with cursos_conn() as conn:
            curso = conn.execute("SELECT status, vagas FROM cursos WHERE id=?", (self.curso_id,)).fetchone()
            if not curso or curso["status"] == "FINALIZADO":
                return await interaction.followup.send(embed=embed_ephemeral("Curso não encontrado ou já finalizado.", "aviso"), ephemeral=True)
            if conn.execute("SELECT 1 FROM inscritos WHERE curso_id=? AND user_id=?", (self.curso_id, interaction.user.id)).fetchone():
                return await interaction.followup.send(embed=embed_ephemeral("Você já está na lista.", "aviso"), ephemeral=True)
            total = conn.execute("SELECT COUNT(*) FROM inscritos WHERE curso_id=? AND tipo='ALUNO'", (self.curso_id,)).fetchone()[0]
            tipo = "ALUNO" if not curso["vagas"] or total < curso["vagas"] else "FILA"
            conn.execute("INSERT INTO inscritos (curso_id,user_id,tipo) VALUES (?,?,?)", (self.curso_id, interaction.user.id, tipo))
        await interaction.followup.send(embed=embed_ephemeral("Inscrição realizada!" if tipo == "ALUNO" else "Curso lotado; você entrou na fila de espera.", "sucesso"), ephemeral=True)
        await atualizar_curso(self.curso_id, interaction.message)
        await log_curso("Nova Inscrição", f"Usuário: {interaction.user.mention}\nCurso ID: {self.curso_id}\nStatus: {tipo}", discord.Color.green())

    async def cancelar(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        with cursos_conn() as conn:
            row = conn.execute("SELECT tipo FROM inscritos WHERE curso_id=? AND user_id=?", (self.curso_id, interaction.user.id)).fetchone()
            if not row:
                return await interaction.followup.send(embed=embed_ephemeral("Você não está inscrito.", "erro"), ephemeral=True)
            conn.execute("DELETE FROM inscritos WHERE curso_id=? AND user_id=?", (self.curso_id, interaction.user.id))
            if row["tipo"] == "ALUNO":
                proximo = conn.execute("SELECT user_id FROM inscritos WHERE curso_id=? AND tipo='FILA' ORDER BY timestamp LIMIT 1", (self.curso_id,)).fetchone()
                if proximo:
                    conn.execute("UPDATE inscritos SET tipo='ALUNO' WHERE curso_id=? AND user_id=?", (self.curso_id, proximo["user_id"]))
        await interaction.followup.send(embed=embed_ephemeral("Removido da lista.", "sucesso"), ephemeral=True)
        await atualizar_curso(self.curso_id, interaction.message)


class ControleCursoView(View):
    def __init__(self, curso_id: int):
        super().__init__(timeout=None)
        self.curso_id = curso_id
        button = Button(label="EMITIR CERTIFICADOS", style=discord.ButtonStyle.gray, emoji="🎓", custom_id=f"curso_emitir:{curso_id}")
        button.callback = self.emitir
        self.add_item(button)

    async def emitir(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not eh_instrutor(interaction.user):
            return await interaction.followup.send(embed=embed_feedback("Erro", "Apenas instrutores."), ephemeral=True)
        with cursos_conn() as conn:
            curso = conn.execute("SELECT * FROM cursos WHERE id=?", (self.curso_id,)).fetchone()
            alunos = conn.execute("SELECT user_id FROM inscritos WHERE curso_id=? AND tipo='ALUNO'", (self.curso_id,)).fetchall()
            if not curso or curso["status"] == "FINALIZADO" or not alunos:
                return await interaction.followup.send(embed=embed_feedback("Aviso", "Curso finalizado, inexistente ou sem alunos."), ephemeral=True)
            conn.execute("UPDATE cursos SET status='FINALIZADO' WHERE id=?", (self.curso_id,))
        canal = bot.get_channel(CANAL_CERTIFICADOS)
        for aluno in alunos:
            with cursos_conn() as conn:
                conn.execute("UPDATE config SET valor=valor+1 WHERE chave='cert_count'")
                numero = conn.execute("SELECT valor FROM config WHERE chave='cert_count'").fetchone()[0]
            embed = discord.Embed(
                title="<:CERTIFICADO:1540945192150896740> CERTIFICADO DE CONCLUSÃO",
                description=(
                    f"O Batalhão Força tática Virtual certifica que o policial <@{aluno['user_id']}> concluiu com êxito o curso **{curso['nome']}**, demonstrando elevado padrão de disciplina, dedicação operacional e comprometimento com a doutrina policial militar.\n\n"
                    "Durante o período de instrução, o policial apresentou desempenho compatível com os princípios que regem as unidades de elite, mantendo postura profissional, respeito à hierarquia e constante busca pelo aprimoramento técnico.\n\n"
                    "Que este certificado represente não apenas a conclusão de uma etapa, mas o fortalecimento do espírito de corpo, da honra policial militar e da missão de servir e proteger a sociedade.\n\n"
                    "O Comando parabeniza pelo empenho demonstrado e incentiva a continuidade no mais alto nível de preparo, mantendo viva a tradição, a disciplina e a excelência operacional.\n\n"
                    f"Curso:\n**`{curso['nome']}`**\n\n"
                    f"Número do Certificado:\n**`ROTA-{datetime.now().year}-{numero:04d}`**\n\n"
                    f"Instrutor Responsável: <@{curso['instrutor_id']}>"
                ),
                color=discord.Color.gold(),
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_image(url=BANNER_CERTIFICADO)
            estilo_curso(embed)
            if canal:
                await canal.send(content=f"<@{aluno['user_id']}>", embed=embed)
        await atualizar_curso(self.curso_id)
        await interaction.followup.send(embed=embed_feedback("Sucesso", "Curso finalizado e certificados emitidos!"), ephemeral=True)


class PainelCursosView(View):
    def __init__(self):
        super().__init__(timeout=None)
        menu = Select(placeholder="Escolha um curso...", options=[discord.SelectOption(label=nome, value=nome) for nome in CURSOS_DISPONIVEIS], custom_id="painel_cursos_select")
        menu.callback = self.selecionar
        self.add_item(menu)

    async def selecionar(self, interaction: discord.Interaction):
        if not eh_instrutor(interaction.user):
            return await interaction.response.send_message(embed=embed_feedback("Erro", "Apenas instrutores podem abrir cursos."), ephemeral=True)
        await interaction.response.send_modal(CursoModal(interaction.data["values"][0]))


class CursoModal(Modal):
    def __init__(self, nome: str):
        super().__init__(title=f"Abrir: {nome}"[:45])
        self.nome = nome
        self.data_curso = TextInput(label="Data", placeholder="Ex: 22/08/2026")
        self.horario = TextInput(label="Hora", placeholder="Ex: 20:00")
        self.local = TextInput(label="Local", placeholder="Ex: Sala de Instrução")
        self.vagas = TextInput(label="Vagas (0 para ilimitado)", default="5")
        for campo in (self.data_curso, self.horario, self.local, self.vagas):
            self.add_item(campo)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            vagas = int(self.vagas.value)
            if vagas < 0:
                raise ValueError
        except ValueError:
            return await interaction.response.send_message(embed=embed_feedback("Erro", "Vagas deve ser um número maior ou igual a zero."), ephemeral=True)
        canal = bot.get_channel(CANAL_CANDIDATOS_CURSOS)
        controle = bot.get_channel(CANAL_CONTROLE_CURSOS)
        if not canal or not controle:
            return await interaction.response.send_message(embed=embed_feedback("Erro", "Canal de cursos não encontrado."), ephemeral=True)
        with cursos_conn() as conn:
            cursor = conn.execute("INSERT INTO cursos (nome,data,horario,local,vagas,instrutor_id,canal_id) VALUES (?,?,?,?,?,?,?)", (self.nome, self.data_curso.value, self.horario.value, self.local.value, vagas, interaction.user.id, CANAL_CANDIDATOS_CURSOS))
            curso_id = cursor.lastrowid
        mensagem = await canal.send(embed=discord.Embed(description="📢 **Publicando edital de curso...**", color=discord.Color.blue()))
        with cursos_conn() as conn:
            conn.execute("UPDATE cursos SET msg_id=? WHERE id=?", (mensagem.id, curso_id))
        await atualizar_curso(curso_id, mensagem)
        controle_embed = discord.Embed(
            title="<:CERTIFICADO:1540945192150896740> Painel de Controle do Curso",
            color=discord.Color.yellow(),
            timestamp=datetime.now(timezone.utc),
        )
        controle_embed.add_field(name="Curso:", value=f"`{self.nome}`", inline=True)
        controle_embed.add_field(name="Vagas:", value=f"`{vagas if vagas > 0 else 'Ilimitadas'}`", inline=True)
        controle_embed.add_field(name="Status Inicial:", value="`AGUARDANDO EMISSÃO`", inline=False)
        controle_embed.add_field(name="Instrutor:", value=interaction.user.mention, inline=False)
        await controle.send(embed=estilo_curso(controle_embed), view=ControleCursoView(curso_id))
        await interaction.response.send_message(embed=embed_feedback("Sucesso", f"Curso de **{self.nome}** aberto com sucesso!"), ephemeral=True)


iniciar_db_cursos()

# ============================
#       SISTEMA DE AUSÊNCIA
# ============================
def embed_painel_ausencia() -> discord.Embed:
    embed = discord.Embed(
        title="<:hora:1540778295115780136> **Sistema de Ausência**",
        description=(
            "Abaixo você poderá emitir uma ausência:\n\n"
            "<:111:1540791811310747759> **Observação:**\n\n"
            "<:ponto:1540777974427553862> Preencha todos os campos obrigatórios com informações precisas.\n"
            "<:ponto:1540777974427553862> Após o envio, um membro da equipe irá analisar sua solicitação.\n"
        ),
        color=discord.Color.yellow(),
    )
    embed.set_image(url=IMAGEM_AUSENCIA_URL)
    estilo_curso(embed)
    return embed


class AusenciaModal(Modal, title="Emitir Ausência"):
    guarnicao = TextInput(label="Unidade", required=True, max_length=50)
    motivo = TextInput(label="Motivo da ausência", style=discord.TextStyle.paragraph, required=True, max_length=300)
    tempo = TextInput(label="Tempo de ausência", required=True, max_length=30)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(
            title="<:hora:1540778295115780136> Registro de Ausência",
            color=discord.Color.yellow(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="<:paineladmin:1540780905902374982> Unidade:", value=f"```{self.guarnicao.value}```", inline=True)
        embed.add_field(name="<:hora:1540778295115780136> Tempo:", value=f"```{self.tempo.value}```", inline=True)
        embed.add_field(name="<:222:1540799996251865108> Motivo:", value=f"```{self.motivo.value}```", inline=False)
        embed.add_field(name="<:CRACHA:1540808611436167208> Solicitante:", value=interaction.user.mention, inline=False)
        embed.set_image(url=IMAGEM_AUSENCIA_URL)
        estilo_curso(embed)

        canal_log = interaction.guild.get_channel(LOG_AUSENCIA_ID) if interaction.guild else None
        if canal_log:
            await canal_log.send(embed=embed)

        await interaction.followup.send(
            embed=embed_ephemeral("Sua ausência foi enviada com sucesso.", "sucesso", "Ausência Enviada"),
            ephemeral=True,
        )


class AusenciaView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Emitir Ausência",
        emoji="<:hora:1540778295115780136>",
        style=discord.ButtonStyle.secondary,
        custom_id="emitir_ausencia",
    )
    async def ausencia(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(AusenciaModal())


# ============================
#   EMOJIS DAS MENSAGENS EPHEMERAL
# ============================
# Troque os valores abaixo por emojis customizados do seu servidor quando
# quiser. Formato de emoji customizado: "<:nome:ID>" (ou "<a:nome:ID>" se
# for animado). Exemplo:
#   "sucesso": "<:sucesso:1234567890123456789>",
EMOJIS = {
    "sucesso": f"<:YES:1540777802935181444>",
    "erro": f"<:111:1540791811310747759>",
    "aviso": f"<:111:1540791811310747759>",
    "info": f"<:111:1540791811310747759>",
    "carregando": f"<:assumirticket:1540778869332906025>",
    "lixeira": f"<:lixeira:1540778211074383932>",
}

# ============================
#         BOT + INTENTS
# ============================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.getenv("TOKEN_ROTA")  # Token do bot (variável de ambiente)


@bot.command(name="painel_ausencia")
async def painel_ausencia(ctx: commands.Context):
    if not isinstance(ctx.author, discord.Member) or not any(role.id == ROLE_VUNESP_ID for role in ctx.author.roles):
        await ctx.send(embed=embed_feedback("Erro", f"Você precisa do cargo <@&{ROLE_VUNESP_ID}> para usar este comando."), delete_after=5)
        return
    canal = bot.get_channel(CANAL_AUSENCIA_ID)
    if canal:
        await canal.purge(limit=5)
        await canal.send(embed=embed_painel_ausencia(), view=AusenciaView())
    await ctx.send("✅ Painel de ausência repostado.", delete_after=5)

# guard para não reenviar painel/verify e não re-sincronizar comandos em reconexões
bot._ready_sent = False

# ============================
#   EMBED PADRÃO PARA MENSAGENS EPHEMERAL
# ============================
def embed_ephemeral(descricao: str, tipo: str = "info", titulo: str | None = None) -> discord.Embed:
    """
    Monta o embed amarelo padrão usado em TODAS as respostas ephemeral do bot.
    'tipo' escolhe o emoji (ver dict EMOJIS lá em cima): sucesso, erro, aviso, info, carregando, lixeira.
    """
    emoji = EMOJIS.get(tipo, "")
    texto = f"{emoji} {descricao}".strip()
    embed = discord.Embed(description=texto, color=discord.Color.yellow())
    if titulo:
        embed.title = titulo
    return embed


def embed_feedback(titulo: str, descricao: str, cor: discord.Color = discord.Color.yellow()) -> discord.Embed:
    """Mantém o formato de feedback usado pelo sistema de cursos."""
    return discord.Embed(title=titulo, description=descricao, color=cor)


def embed_status_credencial(aprovado: bool) -> discord.Embed:
    """
    Embed mostrado (ephemeral) para quem clicou em Aceitar/Recusar,
    no mesmo estilo visual da referência enviada: título com ícone,
    barra colorida na lateral e uma descrição curta e direta.
    """
    if aprovado:
        embed = discord.Embed(
            title=f"<:YES:1540777802935181444> Credencial Aprovada",
            description=(
                "A solicitação foi aprovada com sucesso. Os cargos foram "
                "atribuídos ao usuário e o apelido foi atualizado."
            ),
            color=discord.Color.green(),
        )
    else:
        embed = discord.Embed(
            title=f"<:111:1540791811310747759> Credencial Recusada",
            description=(
                "A solicitação foi recusada com sucesso. O usuário foi "
                "desbloqueado para reenviar se desejar."
            ),
            color=discord.Color.red(),
        )
    return embed


# ============================
#        SISTEMA DE LOGS
# ============================
# Log separado por ação: cada comando manda pro seu próprio canal
# (definido em LOG_CHANNEL_* lá em cima), em vez de tudo cair junto
# no mesmo lugar.

async def enviar_log_canal(guild: discord.Guild, canal_id: int, embed: discord.Embed, contexto: str = ""):
    if not guild:
        return
    if not canal_id:
        print(f"⚠️ Canal de log não configurado para '{contexto}' (valor 0). Log não enviado.")
        return
    canal = guild.get_channel(canal_id)
    if not canal:
        print(f"⚠️ Canal de log '{contexto}' (ID {canal_id}) não encontrado no servidor.")
        return
    try:
        await canal.send(embed=embed)
    except Exception as e:
        print(f"⚠️ Falha ao enviar log de '{contexto}': {e}")


async def enviar_log_embed(guild: discord.Guild, embed: discord.Embed):
    """Log geral do sistema (ex: bot iniciado). Mantido por compatibilidade."""
    await enviar_log_canal(guild, LOG_CHANNEL_SISTEMA, embed, contexto="sistema")


async def enviar_log(guild, titulo, descricao, cor=discord.Color.green()):
    embed = discord.Embed(title=titulo, description=descricao, color=cor)
    embed.set_footer(text="Sistema de Logs - Tropa do Trevo")
    await enviar_log_canal(guild, LOG_CHANNEL_SISTEMA, embed, contexto="sistema")


# ============================
#  HELPERS DE PERMISSÃO
# ============================
def has_authorized_role(member: discord.Member) -> bool:
    if not member or not hasattr(member, "roles"):
        return False
    return any(role.id in CARGOS_AUTORIZADOS for role in member.roles)


async def require_authorized(interaction: discord.Interaction) -> bool:
    if not has_authorized_role(interaction.user):
        await interaction.response.send_message(
            embed=embed_ephemeral("Você não tem permissão (cargo inválido).", "erro"), ephemeral=True
        )
        return False
    return True


async def require_role(interaction: discord.Interaction, role_id: int, nome_cargo: str) -> bool:
    membro = interaction.user
    if not isinstance(membro, discord.Member) or not any(role.id == role_id for role in membro.roles):
        await interaction.response.send_message(
            embed=embed_ephemeral(
                f"Você precisa do cargo <@&{role_id}> para usar este comando.",
                "erro",
            ),
            ephemeral=True,
        )
        return False
    return True


# ============================
#     PAINEL ADMINISTRATIVO
# ============================
class PainelAdminView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📜 Ver Logs", style=discord.ButtonStyle.secondary, custom_id="view_logs")
    async def view_logs(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_authorized_role(interaction.user):
            return await interaction.response.send_message(embed=embed_ephemeral("Sem permissão.", "erro"), ephemeral=True)

        canais = {
            "Sistema": LOG_CHANNEL_SISTEMA,
            "/clearall": LOG_CHANNEL_CLEARALL,
            "/adv": LOG_CHANNEL_ADV,
            "/ban": LOG_CHANNEL_BAN,
            "/mensagem": LOG_CHANNEL_MENSAGEM,
            "Funcional aprovado": LOG_CHANNEL_FUNCIONAL_APROVADO,
            "Funcional recusado": LOG_CHANNEL_FUNCIONAL_RECUSADO,
        }

        linhas = []
        for nome, canal_id in canais.items():
            canal = interaction.guild.get_channel(canal_id) if canal_id else None
            linhas.append(f"**{nome}:** {canal.mention if canal else '⚠️ não configurado'}")

        embed = discord.Embed(
            title="📜 Canais de Log",
            description="\n".join(linhas),
            color=discord.Color.yellow(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def enviar_painel(guild: discord.Guild):
    if not guild:
        return
    canal = guild.get_channel(PAINEL_CHANNEL_ID)
    if canal:
        try:
            await canal.purge(limit=10)
        except Exception:
            pass
        embed = discord.Embed(
            title="🛠 Painel Administrativo",
            description="Gerencie o sistema abaixo:",
            color=discord.Color.yellow(),
        )
        try:
            await canal.send(embed=embed, view=PainelAdminView())
        except Exception:
            pass


# ============================
#        COMANDO /clearall
# ============================
@bot.tree.command(name="clearall", description="Apaga todas as mensagens do canal atual. (apenas VUNESP)")
async def clearall(interaction: discord.Interaction):
    if not await require_role(interaction, 1469854597802754058, "VUNESP"):
        return

    canal = interaction.channel
    guild = interaction.guild
    if canal is None or guild is None:
        return await interaction.response.send_message(embed=embed_ephemeral("Contexto inválido.", "erro"), ephemeral=True)

    await interaction.response.send_message(
        embed=embed_ephemeral(f"Limpando todas as mensagens do canal **{canal.name}**...", "carregando"),
        ephemeral=True,
    )

    try:
        await canal.purge(limit=100)
    except Exception:
        try:
            await canal.purge()
        except Exception:
            pass

    try:
        embed_confirm = discord.Embed(
            title=f"<:lixeira:1540778211074383932> Canal Limpo",
            description=f"As mensagens do canal `{canal.name}` foram apagadas com sucesso!",
            color=discord.Color.yellow(),
        )
        await canal.send(embed=embed_confirm)
    except Exception:
        pass

    embed_log = discord.Embed(
        title=f"<:lixeira:1540778211074383932> Log - Canal Limpo",
        description=(
            f"<:pessoas:1540780605237760050> **Usuário:** {interaction.user.mention}\n\n"
            f"<:pessoas:1540780605237760050> **ID do usuário:** `{interaction.user.id}`\n\n"
            f"<:lixeira:1540778211074383932> **Canal limpo:** {canal.mention}\n\n"
        ),
        color=discord.Color.yellow(),
    )
    embed_log.set_thumbnail(
        url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8b4418&is=6a89f298&hm=ccef0422a39e4382dc5e5b9858c859cb3a0dd81a22eac8f643b85ee6fa955c8f&"
    )    

    embed_log.set_footer(icon_url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8b4418&is=6a89f298&hm=ccef0422a39e4382dc5e5b9858c859cb3a0dd81a22eac8f643b85ee6fa955c8f&", text="Batalhão 9° BPM/M Virtual® Todos direitos reservados.")

    await enviar_log_canal(guild, LOG_CHANNEL_CLEARALL, embed_log, contexto="/clearall")


# ============================
#         MODAL /mensagem
# ============================
class MensagemModal(Modal, title="📢 Enviar Mensagem"):
    conteudo = TextInput(
        label="Conteúdo da mensagem",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000,
    )

    async def _logar_envio(self, interaction: discord.Interaction, qtd_anexos: int = 0):
        embed_log = discord.Embed(
            title=f"<:paineladmin:1540780905902374982> Log - Mensagem Enviada",
            description=(
                f"<:pessoas:1540780605237760050> **Usuário:** {interaction.user.mention}\n\n"
                f"<:pessoas:1540780605237760050> **ID do usuário:** `{interaction.user.id}`\n\n"
                f"<:paineladmin:1540780905902374982> **Canal:** {interaction.channel.mention}\n\n"
                f"<:222:1540799996251865108>  **Anexos:** {qtd_anexos}"
            ),
            color=discord.Color.yellow(),
        )

        embed_log.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8b4418&is=6a89f298&hm=ccef0422a39e4382dc5e5b9858c859cb3a0dd81a22eac8f643b85ee6fa955c8f&"
        )    

        embed_log.set_footer(icon_url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8b4418&is=6a89f298&hm=ccef0422a39e4382dc5e5b9858c859cb3a0dd81a22eac8f643b85ee6fa955c8f&", text="Batalhão 9° BPM/M Virtual® Todos direitos reservados.")

        embed_log.add_field(name=f"<:111:1540791811310747759> Conteúdo:",value=self.conteudo.value[:1024], inline=False)
        await enviar_log_canal(interaction.guild, LOG_CHANNEL_MENSAGEM, embed_log, contexto="/mensagem")

    async def on_submit(self, interaction: discord.Interaction):
        if not has_authorized_role(interaction.user):
            await interaction.response.send_message(
                embed=embed_ephemeral("Você não tem permissão para usar este modal.", "erro"), ephemeral=True
            )
            return

        await interaction.response.send_message(embed=embed_ephemeral("Enviando...", "carregando"), ephemeral=True)

        try:
            msg_inicial = await interaction.channel.send(self.conteudo.value)
        except Exception:
            await interaction.followup.send(
                embed=embed_ephemeral("Não consegui enviar a mensagem inicial (permissão).", "erro"), ephemeral=True
            )
            return

        await interaction.followup.send(
            embed=embed_ephemeral("Responda aquela mensagem com anexos em até 5 minutos.", "info"),
            ephemeral=True,
        )

        def check(m: discord.Message):
            return (
                m.reference
                and m.reference.message_id == msg_inicial.id
                and m.author == interaction.user
                and m.channel == interaction.channel
            )

        try:
            reply = await bot.wait_for("message", timeout=300.0, check=check)
            files = []
            async with aiohttp.ClientSession() as session:
                for a in reply.attachments:
                    try:
                        async with session.get(a.url) as resp:
                            dados = await resp.read()
                            files.append(discord.File(io.BytesIO(dados), filename=a.filename))
                    except Exception:
                        continue

            try:
                await msg_inicial.delete()
                await reply.delete()
            except Exception:
                pass

            try:
                await interaction.channel.send(content=self.conteudo.value, files=files)
            except Exception:
                await interaction.followup.send(
                    embed=embed_ephemeral("Não consegui reenviar a mensagem (permissão).", "erro"), ephemeral=True
                )
                return

            await self._logar_envio(interaction, qtd_anexos=len(files))

        except asyncio.TimeoutError:
            # a mensagem inicial (sem anexos) já foi enviada — loga mesmo assim
            await self._logar_envio(interaction, qtd_anexos=0)
            try:
                await interaction.followup.send(
                    embed=embed_ephemeral("Tempo esgotado. Nenhum anexo recebido.", "aviso"), ephemeral=True
                )
            except Exception:
                pass


@bot.tree.command(name="mensagem", description="Enviar mensagem como o bot. (apenas VUNESP)")
async def mensagem(interaction: discord.Interaction):
    if not await require_role(interaction, 1469854597802754058, "VUNESP"):
        return
    await interaction.response.send_modal(MensagemModal())


# ============================
#      SISTEMA DE ADVs
# ============================
@bot.tree.command(name="advertencia", description="Adiciona ou remove uma advertência. (apenas VUNESP)")
@app_commands.describe(membro="Membro", motivo="Motivo da advertência (obrigatório ao adicionar)", acao="Adicionar ou remover")
@app_commands.choices(acao=[
    app_commands.Choice(name="Adicionar", value="adicionar"),
    app_commands.Choice(name="Remover", value="remover"),
])
async def adv(interaction: discord.Interaction, membro: discord.Member, acao: app_commands.Choice[str], motivo: str = ""):
    if not await require_role(interaction, 1469854597802754058, "VUNESP"):
        return

    if not interaction.user.guild_permissions.kick_members:
        return await interaction.response.send_message(
            embed=embed_ephemeral("Você precisa de permissão para expulsar (kick) para aplicar advertências.", "erro"),
            ephemeral=True,
        )

    # responde já; remover/adicionar cargos envolve chamadas à API do
    # Discord que podem ultrapassar os 3s de janela de resposta
    await interaction.response.defer(ephemeral=True)

    adv1 = interaction.guild.get_role(ID_CARGO_ADV1)
    adv2 = interaction.guild.get_role(ID_CARGO_ADV2)
    adv3 = interaction.guild.get_role(ID_CARGO_ADV3)
    afastado = interaction.guild.get_role(ID_CARGO_AFASTADO)

    if acao.value == "remover":
        historico = await db.a_historico_advertencias(membro.id)
        if not historico:
            return await interaction.followup.send(embed=embed_ephemeral("Esse membro não possui advertências registradas.", "aviso"), ephemeral=True)
        ultima = await db.a_remover_ultima_advertencia(membro.id)
        nivel_removido = ultima["nivel"] if ultima else -1
        cargo_por_nivel = {0: adv1, 1: adv2, 2: adv3, 3: afastado}
        cargo = cargo_por_nivel.get(nivel_removido)
        if cargo and cargo in membro.roles:
            await membro.remove_roles(cargo)
        cargo_restaurado = {1: adv1, 2: adv2, 3: adv3}.get(nivel_removido)
        if cargo_restaurado:
            await membro.add_roles(cargo_restaurado)
        await interaction.followup.send(embed=embed_ephemeral(f"Última advertência de {membro.mention} removida.", "sucesso"), ephemeral=True)

        embed_log = discord.Embed(
            title="<:lixeira:1540778211074383932> **Advertência removida**",
            description=(
                f"<:CRACHA3:1540809884424208394> **Membro:**\n> {membro.mention}\n\n"
                f"<:CRACHA2:1540808930572243004> **Por:**\n> {interaction.user.mention}\n\n"
                f"<:baixar:1540778990615273533> **Nível removido:**\n```{nivel_removido}/2```\n\n"
                f"<:222:1540799996251865108> **Motivo da remoção:**\n```{motivo or 'Não informado'}```"
            ),
            color=discord.Color.orange(),
        )
        embed_log.set_thumbnail(url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8b4418&is=6a89f298&hm=ccef0422a39e4382dc5e5b9858c859cb3a0dd81a22eac8f643b85ee6fa955c8f&")
        embed_log.set_footer(
            text="Batalhão 9° BPM/M Virtual® Todos direitos reservados.",
            icon_url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8b4418&is=6a89f298&hm=ccef0422a39e4382dc5e5b9858c859cb3a0dd81a22eac8f643b85ee6fa955c8f&",
        )
        await enviar_log_canal(interaction.guild, LOG_CHANNEL_ADV, embed_log, contexto="/advertencia remover")
        return

    if not motivo.strip():
        return await interaction.followup.send(embed=embed_ephemeral("Informe o motivo ao adicionar uma advertência.", "erro"), ephemeral=True)

    if afastado in membro.roles:
        return await interaction.followup.send(embed=embed_ephemeral("Esse membro já está afastado.", "aviso"), ephemeral=True)

    if adv3 in membro.roles:
        try:
            await membro.remove_roles(adv3)
            await membro.add_roles(afastado)
            msg = "4ª advertência → AFASTADO"
            nivel = 3
        except Exception:
            return await interaction.followup.send(embed=embed_ephemeral("Erro ao atualizar cargos.", "erro"), ephemeral=True)
    elif adv2 in membro.roles:
        await membro.remove_roles(adv2)
        await membro.add_roles(adv3)
        msg = "2ª advertência aplicada!"
        nivel = 2
    elif adv1 in membro.roles:
        await membro.remove_roles(adv1)
        await membro.add_roles(adv2)
        msg = "1ª advertência aplicada!"
        nivel = 1
    else:
        await membro.add_roles(adv1)    
        msg = "Advertência Verbal aplicada!"
        nivel = verbal = 0

    tipo_msg = "erro" if nivel == 3 else "aviso"
    await interaction.followup.send(embed=embed_ephemeral(msg, tipo_msg), ephemeral=True)

    # persiste no banco
    await db.a_aplicar_advertencia(membro.id, interaction.user.id, motivo, nivel)

    embed = discord.Embed(
        title=f"<:paineladmin:1540780905902374982> **Advertência aplicada**",
        description=
        f"<:CRACHA3:1540809884424208394> **Membro:**\n" 
        f"> {membro.mention}\n\n"

        f"<:CRACHA2:1540808930572243004> **Por:**\n" 
        f"> {interaction.user.mention}\n\n"

        f"<:baixar:1540778990615273533> Advertências aplicadas:\n" 
        f"```{nivel}/2```\n\n"

        f"<:222:1540799996251865108> **Motivo:**\n" 
        f"```{motivo}```",
        color=discord.Color.yellow(),
    )

    embed.set_thumbnail(
        url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8b4418&is=6a89f298&hm=ccef0422a39e4382dc5e5b9858c859cb3a0dd81a22eac8f643b85ee6fa955c8f&"
    )    

    embed.set_footer(icon_url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8b4418&is=6a89f298&hm=ccef0422a39e4382dc5e5b9858c859cb3a0dd81a22eac8f643b85ee6fa955c8f&", text="Batalhão 9° BPM/M Virtual® Todos direitos reservados.")

    await enviar_log_canal(interaction.guild, LOG_CHANNEL_ADV, embed, contexto="/adv")


# ============================
#            BAN
# ============================
@bot.tree.command(name="banimento", description="Adiciona ou remove um banimento. (apenas VUNESP)")
@app_commands.describe(membro="Usuário", motivo="Motivo (obrigatório ao adicionar)", acao="Adicionar ou remover")
@app_commands.choices(acao=[
    app_commands.Choice(name="Adicionar", value="adicionar"),
    app_commands.Choice(name="Remover", value="remover"),
])
async def ban(interaction: discord.Interaction, membro: discord.Member, acao: app_commands.Choice[str], motivo: str = ""):
    if not await require_role(interaction, 1469854597802754058, "VUNESP"):
        return

    if not interaction.user.guild_permissions.ban_members:
        return await interaction.response.send_message(
            embed=embed_ephemeral("Você precisa da permissão de banir para usar este comando.", "erro"), ephemeral=True
        )

    await interaction.response.defer(ephemeral=True)

    if acao.value == "adicionar" and not motivo.strip():
        return await interaction.followup.send(embed=embed_ephemeral("Informe o motivo ao adicionar um banimento.", "erro"), ephemeral=True)

    cargo_banimento = interaction.guild.get_role(ID_CARGO_AFASTADO)
    if not cargo_banimento:
        return await interaction.followup.send(embed=embed_ephemeral("O cargo de banimento não foi encontrado.", "erro"), ephemeral=True)

    try:
        if acao.value == "adicionar":
            if cargo_banimento in membro.roles:
                return await interaction.followup.send(embed=embed_ephemeral("Esse membro já possui o cargo de banimento.", "aviso"), ephemeral=True)
            await membro.add_roles(cargo_banimento, reason=motivo)
            mensagem = f"{membro.mention} recebeu o cargo de banimento e permanecerá no servidor."
        else:
            if cargo_banimento not in membro.roles:
                return await interaction.followup.send(embed=embed_ephemeral("Esse membro não possui o cargo de banimento.", "aviso"), ephemeral=True)
            await membro.remove_roles(cargo_banimento, reason=motivo or "Remoção do banimento")
            mensagem = f"O cargo de banimento foi removido de {membro.mention}."
        await interaction.followup.send(embed=embed_ephemeral(mensagem, "sucesso"), ephemeral=True)
    except discord.Forbidden:
        return await interaction.followup.send(embed=embed_ephemeral("O bot não tem permissão para adicionar ou remover esse cargo.", "erro"), ephemeral=True)

    titulo_acao = "Membro Banido" if acao.value == "adicionar" else "Banimento Removido"
    embed = discord.Embed(
        title=f"<:paineladmin:1540780905902374982> **{titulo_acao}**",
        description=
        f"<:CRACHA3:1540809884424208394> **Membro:**\n" 
        f"> {membro.mention}\n\n"

        f"<:CRACHA2:1540808930572243004> **Por:**\n" 
        f"> {interaction.user.mention}\n\n"

        f"<:222:1540799996251865108> **Motivo:**\n" 
        f"```{motivo}```",
        color=discord.Color.yellow(),
    )

    embed.set_thumbnail(
        url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8b4418&is=6a89f298&hm=ccef0422a39e4382dc5e5b9858c859cb3a0dd81a22eac8f643b85ee6fa955c8f&"
    )    

    embed.set_footer(icon_url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8b4418&is=6a89f298&hm=ccef0422a39e4382dc5e5b9858c859cb3a0dd81a22eac8f643b85ee6fa955c8f&", text="Batalhão 9° BPM/M Virtual® Todos direitos reservados.")

    await enviar_log_canal(interaction.guild, LOG_CHANNEL_BAN, embed, contexto="/banimento")


# ================= CONFIG ROTA =================

CANALETA_SOLICITAR_SET_ID = 1343398652349255758
CARGO_NOVATO_ID = 1345435302285545652
CATEGORIA_TICKET_ID = 1540764062047142081

CANAL_LOGS_ROTA = 1473844393893953679

CARGO_ROTA_ID = 1343645401051431017
CARGO_1CIA_ID = 1540764436078272562
CARGO_2CIA_ID = 1540764610079096842

# ================= PATENTES ROTA =================

PATENTES_ROTA = {
    "Soldado de 2° Classe PM": {
        "roles": [1343408280919050240, 1343645401051431017],
        "emoji": "<:SD:1480800971604103310>",
    },
    "Soldado de 1º Classe PM": {
        "roles": [1343408322774175785, 1343645401051431017, 1345448070904545383, 1474036218193776771],
        "emoji": "<:SD:1480800971604103310>",
    },
    "Cabo PM": {
        "roles": [1343408303417331772, 1343645401051431017, 1345448070904545383, 1474036218193776771],
        "emoji": "<:CABO:1480800948434767965>",
    },
    "3º Sargento PM": {
        "roles": [1343404402219814932, 1343645401051431017, 1345448070904545383, 1474036218193776771],
        "emoji": "<:3SGT:1480800757027573833>",
    },
    "2º Sargento PM": {
        "roles": [1343408106457272462, 1343645401051431017, 1345448070904545383, 1474036218193776771],
        "emoji": "<:2SGT:1480800372267421850>",
    },
    "1º Sargento PM": {
        "roles": [1343408155161264158, 1343645401051431017, 1345448070904545383, 1474036218193776771],
        "emoji": "<:1SGT:1480800346375983226>",
    },
    "Sub-Tenente PM": {
        "roles": [1343727303795933184, 1343645401051431017, 1345448070904545383, 1474036218193776771],
        "emoji": "<:SUBTEN:1480800319553273898>",
    },
    "Aspirante a Oficial PM": {
        "roles": [1343648749381091570, 1343645401051431017, 1475979105773289665, 1479956670502142043],
        "emoji": "<:ASPOFC:1480800296748847205>",
    },
    "2º Tenente PM": {
        "roles": [1343419697294479471, 1343645401051431017, 1472845767411761172, 1474036182215037028],
        "emoji": "<:2TENENTE:1480800246337638511>",
    },
    "1º Tenente PM": {
        "roles": [1343408376302014495, 1343645401051431017, 1472845767411761172, 1474036182215037028],
        "emoji": "<:1TENENTE:1480800221930983538>",
    },
    "Capitão PM": {
        "roles": [1343404318946103346, 1343645401051431017, 1345445863794802791, 1475272157855481938, 1474036182215037028],
        "emoji": "<:CAPITO:1480800193841463367>",
    },
    "Major PM": {
        "roles": [1343401976523784253, 1343645401051431017, 1343758208925175859, 1474036182215037028, 1475272157855481938, 1474200327564693739],
        "emoji": "<:MAJOR:1480800161646116956>",
    },
    "Tenente-Coronel PM": {
        "roles": [1343401212417937468, 1343645401051431017, 1343758208925175859, 1474036182215037028, 1475272157855481938, 1345445339456475286],
        "emoji": "<:TENCEL:1480800122341298186>",
    },
    "Coronel PM": {
        "roles": [1540766907656048755, 1343645401051431017, 1343758208925175859, 1474036182215037028, 1475272157855481938, 1343758574387593298],
        "emoji": "<:CEL:1540765334531735703>",
    },
}

# ================= TICKET =================

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Solicitar Funcional",
        style=discord.ButtonStyle.secondary,
        emoji="<:CRACHA:1540808611436167208>",
        custom_id="ticket_abrir",
    )
    async def abrir_ticket(self, interaction: discord.Interaction, button: Button):
        # checagem via banco: sobrevive a restarts do bot.
        # ticket_aberto_existe só considera status 'aberto' ou
        # 'aguardando_aprovacao' como bloqueio — assim que uma solicitação
        # é aprovada OU recusada, este botão libera automaticamente.
        if await db.a_ticket_aberto_existe(interaction.user.id):
            await interaction.response.send_message(
                embed=embed_ephemeral(
                    "Você já possui uma solicitação de funcional em aberto. "
                    "Aguarde a análise — assim que ela for concluída (aprovada "
                    "ou recusada), você poderá enviar novamente.",
                    "aviso",
                    titulo="Solicitação em Andamento",
                ),
                ephemeral=True,
            )
            return

        # responde já (defer) — criar canal + gravar no banco pode levar
        # mais de 3s em picos de uso, e aí o token da interação expira
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        user = interaction.user

        category = guild.get_channel(CATEGORIA_TICKET_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        canal = await guild.create_text_channel(
            name=f"ticket-{user.id}",
            category=category,
            overwrites=overwrites,
        )

        # ticket_data traz o id interno E o código único (ex: FT-8K2P4X)
        # usado como identificador humano/estável da solicitação.
        ticket_data = await db.a_criar_ticket(user.id, canal.id)
        ticket_id = ticket_data["id"]
        codigo = ticket_data["codigo"]

        view = View()
        view.add_item(SelectPatente(ticket_id))

        view_botao = View()
        view_botao.add_item(
            Button(
                label="Acessar Ticket",
                url=canal.jump_url,
                style=discord.ButtonStyle.link,
                emoji="<:CRACHA:1540808611436167208>",
            )
        )

        embed = discord.Embed(
            title="Ticket Criado com Sucesso",
            description=(
                f"Seu ticket foi criado!\n"
                f"**Clique no botão abaixo** para ir até seu _ticket_.\n\n"
                f"**Código da solicitação:** ||`{codigo}`||\n"  
            ),
            color=discord.Color.yellow(),
        )
        embed.set_footer(icon_url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8b4418&is=6a89f298&hm=ccef0422a39e4382dc5e5b9858c859cb3a0dd81a22eac8f643b85ee6fa955c8f&", text="Batalhão 9°BPM Virtual® Todos direitos reservados.")


        await canal.send(
            f"{user.mention}, Abaixo você poderá selecionar sua patente:  •  Código: ||`{codigo}`||",
            view=view,
        )

        await interaction.followup.send(
            embed=embed,
            view=view_botao,
            ephemeral=True,
        )


# ================= SELECT PATENTE =================

class SelectPatente(Select):
    def __init__(self, ticket_id: int):
        self.ticket_id = ticket_id
        options = []
        for nome, dados in PATENTES_ROTA.items():
            emoji_str = dados.get("emoji")
            emoji = None
            if emoji_str:
                try:
                    emoji = discord.PartialEmoji.from_str(emoji_str)
                except Exception:
                    print(f"⚠️ Emoji inválido para a patente '{nome}': {emoji_str!r} — usando sem emoji.")
                    emoji = None
            else:
                print(f"⚠️ Patente '{nome}' está sem 'emoji' em PATENTES_ROTA — usando sem emoji.")

            options.append(
                discord.SelectOption(
                    label=nome,
                    value=nome,
                    emoji=emoji,
                )
            )
        super().__init__(placeholder="Escolha sua patente", options=options)

    async def callback(self, interaction: discord.Interaction):
        patente_nome = self.values[0]
        dados = PATENTES_ROTA[patente_nome]
        patente_ids = dados.get("roles", [])

        view = View()
        view.add_item(SelectCIA(self.ticket_id, patente_nome, patente_ids))

        await interaction.response.send_message(
            embed=embed_ephemeral("Abra o próximo menu para escolher sua companhia:", "info"),
            view=view,
            ephemeral=True,
        )


# ================= CIA =================

class SelectCIA(Select):
    def __init__(self, ticket_id: int, patente_nome: str, patente_ids: list):
        self.ticket_id = ticket_id
        self.patente_nome = patente_nome
        self.patente_ids = patente_ids

        options = [
            discord.SelectOption(label="1° CIA", value="1CIA"),
            discord.SelectOption(label="2° CIA", value="2CIA"),
        ]
        super().__init__(placeholder="Escolha sua CIA", options=options)

    async def callback(self, interaction: discord.Interaction):
        cia = self.values[0]
        await interaction.response.send_modal(
            DadosPessoaisModal(self.ticket_id, self.patente_nome, self.patente_ids, cia)
        )


# ================= MODAL =================

class DadosPessoaisModal(Modal, title="Registro do Policial"):
    nome = TextInput(label="Nome Completo", required=True, max_length=80)
    passaporte = TextInput(label="Passaporte", required=True, max_length=20)

    def __init__(self, ticket_id: int, patente_nome: str, patente_ids: list, cia: str):
        super().__init__()
        self.ticket_id = ticket_id
        self.patente_nome = patente_nome
        self.patente_ids = patente_ids
        self.cia = cia

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        nome = self.nome.value.strip()
        passaporte = self.passaporte.value.strip()
        cargo_cia_id = CARGO_1CIA_ID if self.cia == "1CIA" else CARGO_2CIA_ID

        await db.a_salvar_dados_pessoais(
            self.ticket_id,
            nome=nome,
            passaporte=passaporte,
            cia=self.cia,
            cargo_cia_id=cargo_cia_id,
            patente_nome=self.patente_nome,
            patente_roles=self.patente_ids,
        )

        # busca o ticket completo (já tem o código gerado na criação)
        ticket = await asyncio.to_thread(db.buscar_ticket_por_canal, interaction.channel.id)
        codigo = ticket["codigo"] if ticket else "—"

        embed = Embed(
            title=f"<:CRACHA:1540808611436167208> **Solicitação de Funcional ||`{codigo}`||**",
            color=discord.Color.yellow(),
        )
        embed.add_field(
            name="<:pessoas:1540780605237760050> Nome:",
            value=f"```{nome}```",
            inline=True,
        )
        embed.add_field(
            name="<:111:1540791811310747759> Identificação:",
            value=f"```{passaporte}```",
            inline=True,
        )
        embed.add_field(
            name="<:222:1540799996251865108> Companhia:",
            value=f"```{self.cia}```",
            inline=False,
        )
        embed.add_field(
            name="<:paineladmin:1540780905902374982> Patente:",
            value=f"```{self.patente_nome}```",
            inline=True,
        )
        embed.add_field(
            name="<:CRACHA:1540808611436167208> Solicitante:",
            value=interaction.user.mention,
            inline=False,
        )
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8b4418&is=6a89f298&hm=ccef0422a39e4382dc5e5b9858c859cb3a0dd81a22eac8f643b85ee6fa955c8f&"
        )
        embed.set_image(
            url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798066678960138/content.png?ex=6a8b4385&is=6a89f205&hm=42f4f0c2b8620d5d10885529900718bafd16db2709f130593b87005d255ff0a2&"
        )
        embed.set_footer(icon_url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8b4418&is=6a89f298&hm=ccef0422a39e4382dc5e5b9858c859cb3a0dd81a22eac8f643b85ee6fa955c8f&", text=f"Batalhão 9° BPM/M Virtual® Todos direitos reservados.")

        try:
            canal_logs = await interaction.client.fetch_channel(CANAL_LOGS_ROTA)
        except Exception:
            await interaction.followup.send(embed=embed_ephemeral("Canal de logs não encontrado.", "erro"), ephemeral=True)
            return

        msg = await canal_logs.send(embed=embed, view=ConfirmarOuFecharView())
        await db.a_registrar_mensagem_log(self.ticket_id, canal_logs.id, msg.id)

        await interaction.followup.send(
            embed=embed_ephemeral(f"Solicitação enviada para avaliação. Código: `{codigo}`", "sucesso"),
            ephemeral=True,
        )


# ================= CONFIRMAR (stateless — busca dados no banco pela mensagem) =================

def _extrair_codigo_do_footer(embed: discord.Embed) -> str | None:
    """Tenta extrair o código (ex: FT-8K2P4X) do rodapé do embed de log, como
    fallback caso a busca pelo ID da mensagem falhe por algum motivo."""
    if not embed or not embed.footer or not embed.footer.text:
        return None
    texto = embed.footer.text
    if "Código:" not in texto:
        return None
    return texto.split("Código:")[-1].strip()


class ConfirmarOuFecharView(View):
    """
    Importante: esta view NÃO guarda user_id/ticket_id na instância.
    Assim ela pode ser re-registrada como view persistente uma única vez
    (com custom_id fixo) e continuar funcionando corretamente mesmo depois
    de o bot reiniciar — o ticket é sempre localizado pelo id da mensagem
    onde o clique aconteceu (e, como reforço, pelo código único gravado
    no rodapé do embed, caso a busca por mensagem não encontre nada).
    """

    def __init__(self):
        super().__init__(timeout=None)

    async def _localizar_ticket(self, interaction: discord.Interaction) -> dict | None:
        ticket = await db.a_buscar_ticket_por_log_message(interaction.message.id)
        if ticket:
            return ticket
        # fallback pelo código gravado no rodapé do embed
        codigo = _extrair_codigo_do_footer(interaction.message.embeds[0]) if interaction.message.embeds else None
        if codigo:
            ticket = await db.a_buscar_ticket_por_codigo(codigo)
        return ticket

    @discord.ui.button(
        label="Aceitar Funcional",
        style=discord.ButtonStyle.gray,
        emoji="<:AMARELO:1495480160319836412>",
        custom_id="confirmar_set",
    )
    async def confirmar(self, interaction: discord.Interaction, button: Button):
        if not has_authorized_role(interaction.user):
            return await interaction.response.send_message(embed=embed_ephemeral("Sem permissão.", "erro"), ephemeral=True)

        # responde a interação AGORA (token expira em ~3s) e só depois faz
        # o trabalho pesado (banco, editar apelido, atribuir cargos etc.)
        await interaction.response.defer(ephemeral=True)

        ticket = await self._localizar_ticket(interaction)
        if not ticket or ticket["status"] != "aguardando_aprovacao":
            return await interaction.followup.send(
                embed=embed_ephemeral("Solicitação não encontrada ou já processada.", "erro"), ephemeral=True
            )

        membro = interaction.guild.get_member(ticket["user_id"])
        if not membro:
            return await interaction.followup.send(
                embed=embed_ephemeral("Membro não encontrado no servidor.", "erro"), ephemeral=True
            )

        novo_apelido = f"#{ticket['passaporte']} | {ticket['nome']}"
        try:
            await membro.edit(nick=novo_apelido)
        except Exception:
            pass

        cargos = []
        for role_id in json.loads(ticket["patente_roles"] or "[]"):
            cargo = interaction.guild.get_role(role_id)
            if cargo:
                cargos.append(cargo)

        cargo_rota = interaction.guild.get_role(CARGO_ROTA_ID)
        if cargo_rota:
            cargos.append(cargo_rota)

        cargo_cia = interaction.guild.get_role(ticket["cargo_cia_id"])
        if cargo_cia:
            cargos.append(cargo_cia)

        if cargos:
            try:
                await membro.add_roles(*cargos)
            except Exception:
                await interaction.followup.send(
                    embed=embed_ephemeral("Erro ao atribuir cargos (verifique permissões do bot).", "erro"),
                    ephemeral=True,
                )
                return

        # status muda para 'aprovado' -> ticket_aberto_existe(user_id) volta a
        # ser False automaticamente, liberando o botão "Solicitar Funcional"
        # (nesse caso o usuário já foi aprovado, então não precisa reabrir).
        await db.a_finalizar_ticket(ticket["id"], "aprovado", interaction.user.id)

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.description = (embed.description or "") + f"\n\n<:CRACHA2:1540808930572243004> **Aprovado por:** {interaction.user.mention}"
        await interaction.message.edit(embed=embed, view=None)

        await interaction.followup.send(embed=embed_status_credencial(aprovado=True), ephemeral=True)

        embed_log = discord.Embed(
            title=f"<:CRACHA2:1540808930572243004> Log - Funcional Aprovada ||`{ticket['codigo']}`||",
            description=(
                f"<:pessoas:1540780605237760050> **Nome:**"
                f"`{ticket['nome']}`\n\n"
                f"<:111:1540791811310747759> **Identificação:**"
                f"`{ticket['passaporte']}`\n\n"
                f"<:222:1540799996251865108> **Companhia:**"
                f"`{ticket['cia']}`\n\n"             
                f"<:paineladmin:1540780905902374982> **Patente:**"
                f"`{ticket['patente_nome']}`\n\n"   
                f"<:CRACHA:1540808611436167208> **Solicitante:**"
                f"<@{ticket['user_id']}>\n\n"               
                f"<:CRACHA:1540808611436167208> **Aprovado por:** {interaction.user.mention}"
            ),  
            
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )
        await enviar_log_canal(interaction.guild, LOG_CHANNEL_FUNCIONAL_APROVADO, embed_log, contexto="funcional aprovado")

        canal = interaction.guild.get_channel(ticket["canal_id"])
        if canal:
            await asyncio.sleep(5)
            try:
                await canal.delete()
            except Exception:
                pass

    @discord.ui.button(
        label="Recusar Funcional",
        style=discord.ButtonStyle.gray,
        emoji="<:x1:1495508233647952062>",
        custom_id="recusar_set",
    )
    async def cancelar(self, interaction: discord.Interaction, button: Button):
        if not has_authorized_role(interaction.user):
            return await interaction.response.send_message(embed=embed_ephemeral("Sem permissão.", "erro"), ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        ticket = await self._localizar_ticket(interaction)
        if not ticket or ticket["status"] != "aguardando_aprovacao":
            return await interaction.followup.send(
                embed=embed_ephemeral("Solicitação não encontrada ou já processada.", "erro"), ephemeral=True
            )

        # status muda para 'recusado' -> ticket_aberto_existe(user_id) volta a
        # ser False automaticamente, liberando o botão "Solicitar Funcional"
        # para o usuário poder enviar de novo.
        await db.a_finalizar_ticket(ticket["id"], "recusado", interaction.user.id)

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.description = (embed.description or "") + f"\n\n<:CRACHA3:1540809884424208394> **Recusado por:** {interaction.user.mention}"
        await interaction.message.edit(embed=embed, view=None)

        await interaction.followup.send(embed=embed_status_credencial(aprovado=False), ephemeral=True)

        embed_log = discord.Embed(
            title=f"<:CRACHA3:1540809884424208394> Log - Funcional Recusada ||`{ticket['codigo']}`||",
            description=(
                f"<:pessoas:1540780605237760050> **Nome:**"
                f"`{ticket['nome']}`\n\n"
                f"<:111:1540791811310747759> **Identificação:**"
                f"`{ticket['passaporte']}`\n\n"
                f"<:222:1540799996251865108> **Companhia:**"
                f"`{ticket['cia']}`\n\n"             
                f"<:paineladmin:1540780905902374982> **Patente:**"
                f"`{ticket['patente_nome']}`\n\n"   
                f"<:CRACHA:1540808611436167208> **Solicitante:**"
                f"<@{ticket['user_id']}>\n\n"                
                f"<:CRACHA3:1540809884424208394> **Recusado por:** {interaction.user.mention}"
            ),

            color=discord.Color.red(),
            timestamp=discord.utils.utcnow(),
        )
        await enviar_log_canal(interaction.guild, LOG_CHANNEL_FUNCIONAL_RECUSADO, embed_log, contexto="funcional recusado")

        canal = interaction.guild.get_channel(ticket["canal_id"])
        if canal:
            await asyncio.sleep(5)
            try:
                await canal.delete()
            except Exception:
                pass


# ================= BUSCAR FUNCIONAL POR CÓDIGO =================

@bot.tree.command(
    name="buscar-funcional",
    description="Consulta uma solicitação de funcional pelo código (ex: FT-8K2P4X). (apenas P/1)",
)
async def buscar_funcional(interaction: discord.Interaction, codigo: str):
    if not await require_role(interaction, ROLE_ADMIN_FUNCIONAL_ID, "P/1"):
        return

    await interaction.response.defer(ephemeral=True)

    ticket = await db.a_buscar_ticket_por_codigo(codigo)
    if not ticket:
        return await interaction.followup.send(
            embed=embed_ephemeral(f"Nenhuma solicitação encontrada para o código ||`{codigo}`||.", "erro"),
            ephemeral=True,
        )

    status_legivel = {
        "aberto": "🟡 Aberto (aguardando dados)",
        "aguardando_aprovacao": "🟠 Aguardando aprovação",
        "aprovado": "🟢 Aprovado",
        "recusado": "🔴 Recusado",
    }.get(ticket["status"], ticket["status"])

    embed = discord.Embed(
        title=f"<:CRACHA:1540808611436167208> Solicitação `{ticket['codigo']}`",
        description=(
            f"<:pessoas:1540780605237760050> **Nome:** {ticket.get('nome') or '—'}\n\n"
            f"<:111:1540791811310747759> **Identificação:** {ticket.get('passaporte') or '—'}\n\n"
            f"<:222:1540799996251865108> **Companhia:** {ticket.get('cia') or '—'}\n\n"
            f"<:paineladmin:1540780905902374982> **Patente:** {ticket.get('patente_nome') or '—'}\n\n"
            f"<:CRACHA:1540808611436167208> **Solicitante:** <@{ticket['user_id']}>\n\n"         
            f"<:assumirticket:1540778869332906025> **Status:** {status_legivel}"
        ),
        color=discord.Color.yellow(),
    )
    await interaction.followup.send(embed=embed, ephemeral=True)


# ================= BOLETINS =================

rascunhos_boletim: dict[int, dict] = {}


def salvar_rascunho_boletim(user_id: int, companhia: str, partes: list[str]) -> None:
    rascunhos_boletim[user_id] = {
        "companhia": companhia,
        "partes": partes,
        "expira_em": datetime.now() + timedelta(hours=RASCUNHO_EXPIRACAO_HORAS),
    }


def obter_rascunho_boletim(user_id: int) -> dict | None:
    rascunho = rascunhos_boletim.get(user_id)
    if rascunho and datetime.now() < rascunho["expira_em"]:
        return rascunho
    rascunhos_boletim.pop(user_id, None)
    return None


def limpar_rascunho_boletim(user_id: int) -> None:
    rascunhos_boletim.pop(user_id, None)


async def tarefa_limpeza_boletim() -> None:
    await bot.wait_until_ready()
    while not bot.is_closed():
        agora = datetime.now()
        expirados = [
            user_id
            for user_id, rascunho in rascunhos_boletim.items()
            if agora >= rascunho["expira_em"]
        ]
        for user_id in expirados:
            rascunhos_boletim.pop(user_id, None)
        await asyncio.sleep(600)


def embed_sistema_boletim(descricao: str, titulo: str | None = None) -> discord.Embed:
    embed = discord.Embed(description=descricao, color=discord.Color.yellow())
    if titulo:
        embed.title = titulo
    return embed


def montar_embed_boletim(companhia: str, membro: discord.Member, respostas: list[tuple[str, str]]) -> discord.Embed:
    embed = discord.Embed(title=f"BOLETIM INTERNO | {companhia}", color=discord.Color.yellow())
    for titulo, resposta in respostas:
        embed.add_field(name=titulo, value=f"```{resposta or '_Não informado_'}```", inline=False)
    embed.add_field(name="<:CERTIFICADO:1540945192150896740> Assina:", value=membro.mention, inline=False)
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8c9598&is=6a8b4418&hm=0b9faa95c5cc5c9231eb5090e3ba60d87bbcf067a833b9fe9c655d32bc737a87&")
    embed.set_image(url="https://cdn.discordapp.com/attachments/1444735189765849320/1541312924428279859/9_bpm_INSCRICOES_2.png?ex=6a8dcbc5&is=6a8c7a45&hm=c3ec6969dec0b908af952d11a6d8dedcd88ff77985cf90db284c2a0c3062163b&")
    embed.set_footer(text="Batalhão 9° BPM/M Virtual® Todos direitos reservados", icon_url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8c9598&is=6a8b4418&hm=0b9faa95c5cc5c9231eb5090e3ba60d87bbcf067a833b9fe9c655d32bc737a87&")
    return embed


class BoletimModal(Modal, title="Boletim Interno"):
    def __init__(self, companhia: str, rascunho: list[str] | None = None):
        super().__init__()
        self.companhia = companhia
        partes = rascunho or ["", "", "", ""]
        campos = [
            ("🪪 1° PARTE — Serviços Diários", "Descreva os serviços diários..."),
            ("📁 2° PARTE — Instrução e Operações", "Descreva instruções e operações policiais..."),
            ("📆 3° PARTE — Assuntos Gerais", "Descreva assuntos gerais e administrativos..."),
            ("📋 4° PARTE — Justiça e Disciplina", "Descreva questões de justiça e disciplina..."),
        ]
        self.partes = []
        for indice, (label, placeholder) in enumerate(campos):
            campo = TextInput(
                label=label,
                style=discord.TextStyle.paragraph,
                placeholder=placeholder,
                default=partes[indice],
                max_length=1024,
            )
            self.partes.append(campo)
            self.add_item(campo)

    async def on_submit(self, interaction: discord.Interaction):
        respostas = [campo.value for campo in self.partes]
        salvar_rascunho_boletim(interaction.user.id, self.companhia, respostas)
        embed_boletim = montar_embed_boletim(
            self.companhia,
            interaction.user,
            [
                ("🪪 1° PARTE — Serviços Diários", respostas[0]),
                ("📁 2° PARTE — Instrução e Operações", respostas[1]),
                ("📆 3° PARTE — Assuntos Gerais", respostas[2]),
                ("📋 4° PARTE — Justiça e Disciplina", respostas[3]),
            ],
        )
        await interaction.response.send_message(
            embeds=[
                embed_sistema_boletim(
                    "Revise as informações abaixo e confirme o envio.",
                    "<:PRANCHETA:1541310906334449734> Prévia do seu Boletim",
                ),
                embed_boletim,
            ],
            view=PreviewBoletimView(embed_boletim, self.companhia),
            ephemeral=True,
        )


class PreviewBoletimView(View):
    def __init__(self, embed: discord.Embed, companhia: str):
        super().__init__(timeout=300)
        self.embed = embed
        self.companhia = companhia

    @discord.ui.button(label="Confirmar e Enviar", emoji=discord.PartialEmoji(name="baixar", id=1540778990615273533), style=discord.ButtonStyle.secondary, custom_id="boletim_confirmar")
    async def confirmar(self, interaction: discord.Interaction, button: Button):
        canal_id = CANAL_BOLETINS.get(self.companhia)
        canal = interaction.guild.get_channel(canal_id) if interaction.guild and canal_id else None
        if not canal:
            await interaction.response.edit_message(embed=embed_sistema_boletim("❌ Canal de destino não encontrado. Contate um administrador."), view=None)
            return
        await canal.send(embed=self.embed)
        limpar_rascunho_boletim(interaction.user.id)
        await interaction.response.edit_message(embed=embed_sistema_boletim(f"<:PASTA:1541310811522203768> Boletim enviado com sucesso para {canal.mention}!"), view=None)

    @discord.ui.button(label="Editar Boletim", emoji=discord.PartialEmoji(name="assumirticket", id=1540778869332906025), style=discord.ButtonStyle.secondary, custom_id="boletim_editar")
    async def editar(self, interaction: discord.Interaction, button: Button):
        rascunho = obter_rascunho_boletim(interaction.user.id)
        await interaction.response.send_modal(BoletimModal(self.companhia, rascunho["partes"] if rascunho else None))

    @discord.ui.button(label="Salvar Rascunho", emoji=discord.PartialEmoji(name="222", id=1540799996251865108), style=discord.ButtonStyle.secondary, custom_id="boletim_salvar")
    async def salvar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(embed=embed_sistema_boletim(f"<:222:1540799996251865108> Rascunho salvo por **`{RASCUNHO_EXPIRACAO_HORAS} horas`**."), view=None)


class RascunhoBoletimView(View):
    def __init__(self, companhia: str, partes: list[str]):
        super().__init__(timeout=60)
        self.companhia = companhia
        self.partes = partes

    @discord.ui.button(label="Continuar rascunho", emoji=discord.PartialEmoji(name="PASTA", id=1541310811522203768), style=discord.ButtonStyle.secondary, custom_id="boletim_continuar")
    async def continuar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(BoletimModal(self.companhia, self.partes))

    @discord.ui.button(label="Começar do zero", emoji=discord.PartialEmoji(name="lixeira", id=1540778211074383932), style=discord.ButtonStyle.secondary, custom_id="boletim_zerar")
    async def zerar(self, interaction: discord.Interaction, button: Button):
        limpar_rascunho_boletim(interaction.user.id)
        await interaction.response.send_modal(BoletimModal(self.companhia))


class SelectCompanhiaBoletim(Select):
    def __init__(self, companhias: list[str]):
        super().__init__(placeholder="Selecione a companhia", options=[discord.SelectOption(label=nome, value=nome) for nome in companhias])

    async def callback(self, interaction: discord.Interaction):
        companhia = self.values[0]
        rascunho = obter_rascunho_boletim(interaction.user.id)
        partes = rascunho["partes"] if rascunho and rascunho["companhia"] == companhia else None
        await interaction.response.send_modal(BoletimModal(companhia, partes))


class SelectCompanhiaBoletimView(View):
    def __init__(self, companhias: list[str]):
        super().__init__(timeout=60)
        self.add_item(SelectCompanhiaBoletim(companhias))


class BotaoBoletim(Button):
    def __init__(self):
        super().__init__(label="Emitir Boletim", emoji=discord.PartialEmoji(name="BOLETIM", id=1541310958964576276), style=discord.ButtonStyle.secondary, custom_id="botao_emitir_boletim")

    async def callback(self, interaction: discord.Interaction):
        membro = interaction.user
        if discord.utils.get(membro.roles, id=ID_CARGO_GERAL_BOLETIM):
            companhias = list(CANAL_BOLETINS)
        else:
            companhias = list({CARGOS_AUTORIZADOS_BOLETIM[cargo.id] for cargo in membro.roles if cargo.id in CARGOS_AUTORIZADOS_BOLETIM})
        if not companhias:
            await interaction.response.send_message(embed=embed_sistema_boletim("❌ Você não tem permissão para emitir boletins."), ephemeral=True)
            return
        if len(companhias) == 1:
            companhia = companhias[0]
            rascunho = obter_rascunho_boletim(membro.id)
            if rascunho and rascunho["companhia"] == companhia:
                expira = rascunho["expira_em"].strftime("%H:%M de %d/%m/%Y")
                await interaction.response.send_message(embed=embed_sistema_boletim(f"Você tem um rascunho salvo que expira às **`{expira}`**.\n\nDeseja continuar de onde parou ou começar do zero?", "<:BOLETIM:1541310958964576276> Rascunho encontrado"), view=RascunhoBoletimView(companhia, rascunho["partes"]), ephemeral=True)
            else:
                await interaction.response.send_modal(BoletimModal(companhia))
        else:
            await interaction.response.send_message(embed=embed_sistema_boletim("Selecione a companhia para emitir o boletim:"), view=SelectCompanhiaBoletimView(companhias), ephemeral=True)


class BoletimView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(BotaoBoletim())


@bot.tree.command(name="boletim", description="Envia o painel de boletim interno")
async def boletim(interaction: discord.Interaction):
    if not await require_role(interaction, ID_CARGO_P1_BOLETIM, f"<@&{ID_CARGO_P1_BOLETIM}>"):
        return
    embed = discord.Embed(
        title="<:BOLETIM:1541310958964576276> Sistema de Boletim Interno",
        description=(
            "Clique no botão abaixo para iniciar um boletim.\n\n"
            "<:111:1540791811310747759> **Observações:**\n\n"
            "<:ponto:1540777974427553862> O boletim será salvo como rascunho até que seja enviado.\n\n"
            "<:ponto:1540777974427553862> Você pode editar o boletim antes de enviá-lo.\n\n"
            "<:ponto:1540777974427553862> Rascunhos ficam disponíveis por `24 horas`.\n\n"
            "<:ponto:1540777974427553862> Apenas membros com cargos autorizados podem emitir boletins:\n\n"
            f"(<@&{ID_CARGO_P1_BOLETIM}> / <@&{ID_CARGO_VUNESP_BOLETIM}>)\n\n"
            f"<:ponto:1540777974427553862> O boletim será enviado para <#{CANAL_BOLETINS['9°BPM']}>.\n\n"
            "<:ponto:1540777974427553862> Qualquer dúvida, solicite ajuda à equipe."
        ),
        color=discord.Color.yellow(),
    )
    embed.set_image(url="https://cdn.discordapp.com/attachments/1444735189765849320/1540797986068627598/9_bpm_SOLICITAR_FUNCIONAL_.png?ex=6a8b4372&is=6a89f1f2&hm=3817fcf103b86728f40bdc0b34c8836cdd3512202c519fa7714ef18122861fac&")
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8c9598&is=6a8b4418&hm=0b9faa95c5cc5c9231eb5090e3ba60d87bbcf067a833b9fe9c655d32bc737a87&")
    embed.set_footer(text="Batalhão 9° BPM/M Virtual® Todos direitos reservados", icon_url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8c9598&is=6a8b4418&hm=0b9faa95c5cc5c9231eb5090e3ba60d87bbcf067a833b9fe9c655d32bc737a87&")
    await interaction.response.send_message(embed=embed, view=BoletimView())


# ================= INSCRIÇÕES =================

def carregar_inscricoes() -> dict:
    if not os.path.exists(INSCRICOES_DB_PATH):
        with open(INSCRICOES_DB_PATH, "w", encoding="utf-8") as arquivo:
            json.dump({}, arquivo)
    try:
        with open(INSCRICOES_DB_PATH, "r", encoding="utf-8") as arquivo:
            conteudo = arquivo.read().strip()
        if not conteudo:
            return {}
        dados = json.loads(conteudo)
        return dados if isinstance(dados, dict) else {}
    except (OSError, json.JSONDecodeError):
        print("⚠️ inscricoes.json vazio ou inválido; iniciando banco de inscrições vazio.")
        return {}


def salvar_inscricoes(dados: dict) -> None:
    with open(INSCRICOES_DB_PATH, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)


def bloqueio_inscricao(user_id: int, dados: dict | None = None) -> str | None:
    dados = carregar_inscricoes() if dados is None else dados
    if str(user_id) in dados.get("blacklist", {}):
        return "Você está na blacklist e não pode fazer inscrição."
    registros = [
        item for item in dados.values()
        if isinstance(item, dict) and item.get("userId") == str(user_id)
    ]
    if any(item.get("status") == "aprovado" for item in registros):
        return "Você já foi aprovado e não pode fazer outra inscrição."
    if any(item.get("status") == "pendente" for item in registros):
        return "Você já tem uma inscrição em aberto."
    return None


def codigo_inscricao() -> str:
    dados = carregar_inscricoes()
    while True:
        codigo = "INS-" + "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=6))
        if codigo not in dados:
            return codigo


class InscricaoModal(Modal, title="Ficha de Inscrição - PM"):
    nome = TextInput(label="Nome In-Game", max_length=50)
    idade = TextInput(label="Idade In-Narnia", max_length=10)
    identificacao = TextInput(label="Identificação (ID)", max_length=20)
    experiencia = TextInput(label="Experiência Operacional", style=discord.TextStyle.paragraph, max_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        dados = carregar_inscricoes()
        bloqueio = bloqueio_inscricao(interaction.user.id, dados)
        if bloqueio:
            await interaction.response.send_message(embed=embed_ephemeral(bloqueio, "aviso"), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        codigo = codigo_inscricao()
        dados[codigo] = {
            "codigo": codigo,
            "userId": str(interaction.user.id),
            "username": str(interaction.user),
            "nome": self.nome.value,
            "idade": self.idade.value,
            "id": self.identificacao.value,
            "exp": self.experiencia.value,
            "status": "pendente",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        salvar_inscricoes(dados)

        embed = discord.Embed(
            title=f"<:CRACHA:1540808611436167208> Inscrição Recebida - ||`{codigo}`||",
            color=discord.Color.from_rgb(255, 204, 0),
        )
        embed.add_field(name="<:pessoas:1540780605237760050> Nome In-Game:", value=f"**```{self.nome.value}```**", inline=False)
        embed.add_field(name="<:hora:1540778295115780136> Idade In-Narnia:", value=f"**```{self.idade.value}```**", inline=True)
        embed.add_field(name="<:111:1540791811310747759> Identificação (ID):", value=f"**```{self.identificacao.value}```**", inline=True)
        embed.add_field(name="<:222:1540799996251865108> Experiência Operacional:", value=f"**```{self.experiencia.value}```**", inline=False)
        embed.add_field(name="<:CRACHA:1540808611436167208> Solicitante:", value=interaction.user.mention, inline=False)
        embed.set_image(url="https://cdn.discordapp.com/attachments/1444735189765849320/1541186562304249916/9_bpm_INSCRICOES_.png?ex=6a8cad56&is=6a8b5bd6&hm=b009c2fe3f7f4f62cce3091b34e7249e6149a7befef88837528e7b822d6ec3b1&")
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8c9598&is=6a8b4418&hm=0b9faa95c5cc5c9231eb5090e3ba60d87bbcf067a833b9fe9c655d32bc737a87&")
        embed.set_footer(text="Batalhão 9° BPM/M Virtual® Todos os direitos reservados.")

        canal = interaction.client.get_channel(LOG_CHANNEL_INSCRICOES)
        if canal:
            await canal.send(embed=embed, view=ViewDecisaoInscricao(codigo))
        await interaction.followup.send(
            embed=embed_ephemeral(f"Inscrição enviada. Código: ||`{codigo}`||", "sucesso"),
            ephemeral=True,
        )


class ViewInscricao(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fazer Inscrição", style=discord.ButtonStyle.secondary, custom_id="abrir_inscricao")
    async def abrir(self, interaction: discord.Interaction, button: Button):
        bloqueio = bloqueio_inscricao(interaction.user.id)
        if bloqueio:
            await interaction.response.send_message(embed=embed_ephemeral(bloqueio, "aviso"), ephemeral=True)
            return
        await interaction.response.send_modal(InscricaoModal())


class DecisaoInscricao(Button):
    def __init__(self, codigo: str, aprovado: bool):
        self.codigo = codigo
        self.aprovado = aprovado
        acao = "aprovar" if aprovado else "reprovar"
        super().__init__(
            label=f"Aprovar" if aprovado else f"Reprovar", style=discord.ButtonStyle.secondary if aprovado else discord.ButtonStyle.secondary, custom_id=f"insc_{acao}:{codigo}")

    async def callback(self, interaction: discord.Interaction):
        if not has_authorized_role(interaction.user):
            await interaction.response.send_message(embed=embed_ephemeral("Sem permissão.", "erro"), ephemeral=True)
            return
        dados = carregar_inscricoes()
        registro = dados.get(self.codigo)
        if not registro or registro.get("status") != "pendente":
            await interaction.response.send_message(embed=embed_ephemeral("Inscrição não encontrada ou já processada.", "erro"), ephemeral=True)
            return

        registro["status"] = "aprovado" if self.aprovado else "reprovado"
        registro["decididoPor"] = str(interaction.user)
        salvar_inscricoes(dados)

        membro = interaction.guild.get_member(int(registro["userId"])) if interaction.guild else None
        if self.aprovado and membro:
            cargo = interaction.guild.get_role(ROLE_AUTOROLE_ID)
            if cargo:
                try:
                    await membro.add_roles(cargo)
                except discord.HTTPException as erro:
                    print(f"Erro ao adicionar cargo da inscrição: {erro}")

        mensagem = "Inscrição aprovada." if self.aprovado else "Inscrição reprovada."
        embed_original = interaction.message.embeds[0] if interaction.message.embeds else discord.Embed()
        embed_original.title = (
            f"<:CRACHA2:1540808930572243004> Inscrição Aprovada - ||`{self.codigo}`||"
            if self.aprovado else
            f"<:CRACHA3:1540809884424208394> Inscrição Reprovada - ||`{self.codigo}`||"
        )
        embed_original.color = discord.Color.green() if self.aprovado else discord.Color.red()
        embed_original.add_field(
            name=(
                "<:CRACHA2:1540808930572243004> Aprovado por:"
                if self.aprovado
                else "<:CRACHA3:1540809884424208394> Reprovado por:"
            ),
            value=interaction.user.mention,
            inline=True,
        )
        await interaction.response.edit_message(embed=embed_original, view=None)
        await interaction.followup.send(embed=embed_ephemeral(mensagem, "sucesso" if self.aprovado else "aviso"), ephemeral=True)

        if membro:
            try:
                if self.aprovado:
                    dm_embed = discord.Embed(
                        title="<:CRACHA2:1540808930572243004> Parabéns! Inscrição Aprovada!",
                        description=(
                            f"Sua inscrição **`{self.codigo}`** foi **aprovada**!\n"
                            "Bem-vindo ao Batalhão. Você recebeu o cargo **Sem Set**.\n\n"
                            "Para dar continuidade ao processo seletivo, acesse o canal "
                            "<#1343398652349255758> e siga as instruções fornecidas.\n\n"
                        ),
                        color=discord.Color.from_rgb(255, 204, 0),
                    )
                else:
                    dm_embed = discord.Embed(
                        title="<:CRACHA3:1540809884424208394> Inscrição Reprovada",
                        description=(
                            f"Sua inscrição **`{self.codigo}`** foi **reprovada**.\n"
                            "Aguarde futuros processos seletivos.\n"
                        ),
                        color=discord.Color.from_rgb(255, 204, 0),
                    )

                dm_embed.set_footer(
                    text="Batalhão 9° BPM/M Virtual® Todos os direitos reservados.",
                    icon_url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8c9598&is=6a8b4418&hm=0b9faa95c5cc5c9231eb5090e3ba60d87bbcf067a833b9fe9c655d32bc737a87&",
                )
                dm_embed.set_thumbnail(
                    url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8c9598&is=6a8b4418&hm=0b9faa95c5cc5c9231eb5090e3ba60d87bbcf067a833b9fe9c655d32bc737a87&"
                )
                await membro.send(embed=dm_embed)
            except discord.HTTPException:
                pass


class ViewDecisaoInscricao(View):
    def __init__(self, codigo: str):
        super().__init__(timeout=None)
        self.add_item(DecisaoInscricao(codigo, True))
        self.add_item(DecisaoInscricao(codigo, False))


@bot.tree.command(name="inscricao", description="Abre o painel de inscrições do concurso. (Apenas Instrutores)")
async def inscricao(interaction: discord.Interaction):
    if not await require_role(interaction, ROLE_INSTRUTOR_ID, f"<@&{ROLE_INSTRUTOR_ID}>"):
        return
    embed = discord.Embed(
        title="<:Logo_PMESP:1541187750932389908> Concurso Batalhão 9° BPM/M Virtual®",
        description=(
            "Bem-vindo ao processo seletivo interno da **Polícia Militar**!\n\n"
            "Preencha o formulário de inscrição clicando no botão abaixo.\n"
            "Sua inscrição será analisada pelos superiores do batalhão.\n\n"
            "<:CERTIFICADO:1540945192150896740> Requisitos:\n\n"
            "<:ponto:1540777974427553862> Idade mínima de 18 anos.\n"
            "<:ponto:1540777974427553862> Ensino médio completo.\n"
            "<:ponto:1540777974427553862> Comprometimento.\n"
            "<:ponto:1540777974427553862> Respeito à hierarquia.\n"
            "<:ponto:1540777974427553862> Disponibilidade.\n\n"
            "<:111:1540791811310747759> Dúvidas: entre em contato com a equipe de RH."
        ),
        color=discord.Color.from_rgb(255, 204, 0),
    )
    embed.set_image(url="https://cdn.discordapp.com/attachments/1444735189765849320/1541186562304249916/9_bpm_INSCRICOES_.png?ex=6a8cad56&is=6a8b5bd6&hm=b009c2fe3f7f4f62cce3091b34e7249e6149a7befef88837528e7b822d6ec3b1&")
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8c9598&is=6a8b4418&hm=0b9faa95c5cc5c9231eb5090e3ba60d87bbcf067a833b9fe9c655d32bc737a87&")
    embed.set_footer(text="Batalhão 9° BPM/M Virtual® Todos os direitos reservados.")
    await interaction.response.send_message(embed=embed, view=ViewInscricao())


@bot.tree.command(name="blacklist-inscricao", description="Adiciona ou remove um membro da blacklist. (Apenas Instrutores)")
@app_commands.describe(membro="Membro da blacklist", acao="Adicionar ou remover")
@app_commands.choices(acao=[app_commands.Choice(name="Adicionar", value="adicionar"), app_commands.Choice(name="Remover", value="remover")])
async def blacklist_inscricao(interaction: discord.Interaction, membro: discord.Member, acao: app_commands.Choice[str]):
    if not await require_role(interaction, ROLE_INSTRUTOR_ID, f"<@&{ROLE_INSTRUTOR_ID}>"):
        return
    dados = carregar_inscricoes()
    blacklist = dados.setdefault("blacklist", {})
    if acao.value == "adicionar":
        blacklist[str(membro.id)] = {"username": str(membro), "por": str(interaction.user), "timestamp": datetime.now(timezone.utc).isoformat()}
        mensagem = f"{membro.mention} foi adicionado à blacklist."
    else:
        blacklist.pop(str(membro.id), None)
        mensagem = f"{membro.mention} foi removido da blacklist."
    salvar_inscricoes(dados)
    await interaction.response.send_message(embed=embed_ephemeral(mensagem, "sucesso"), ephemeral=True)


# ================= COMANDOS =================
@bot.tree.command(name="comandos", description="Lista os comandos do bot e os cargos autorizados")
async def comandos(interaction: discord.Interaction):
    embed = discord.Embed(
        title="<:paineladmin:1540780905902374982> Comandos do Bot",
        description="Confira abaixo os comandos disponíveis, suas funções e os cargos autorizados a utilizá-los.",
        color=discord.Color.yellow(),
    )
    comandos_lista = [
        ("/comandos", "Exibe esta lista de comandos.", "Todos os membros"),
        ("/clearall", "Apaga todas as mensagens do canal atual.", f"<@&{ROLE_VUNESP_ID}>"),
        ("/mensagem", "Envia uma mensagem como o bot, com suporte a anexos.", f"<@&{ROLE_VUNESP_ID}>"),
        ("/advertencia", "Adiciona ou remove uma advertência de um membro.", f"<@&{ROLE_VUNESP_ID}>"),
        ("/banimento", "Adiciona ou remove o cargo de banimento de um membro.", f"<@&{ROLE_VUNESP_ID}>"),
        ("/buscar-funcional", "Consulta uma solicitação de funcional pelo código.", f"<@&{ROLE_ADMIN_FUNCIONAL_ID}>"),
        ("/boletim", "Abre o painel para emissão de boletim interno.", f"<@&{ID_CARGO_P1_BOLETIM}>"),
        ("/inscricao", "Publica o painel de inscrições do concurso.", f"<@&{ROLE_INSTRUTOR_ID}>"),
        ("/blacklist-inscricao", "Adiciona ou remove um membro da blacklist de inscrições.", f"<@&{ROLE_INSTRUTOR_ID}>"),
    ]
    for nome, finalidade, cargo in comandos_lista:
        embed.add_field(
            name=nome,
            value=f"**Função:** {finalidade}\n**Cargo autorizado:** {cargo}",
            inline=False,
        )
    embed.set_image(url="https://cdn.discordapp.com/attachments/1444735189765849320/1541631607457189958/9_bpm_COMANDOS.png?ex=6a8e4bd1&is=6a8cfa51&hm=8b17544ee60132ce685bc14c23d5a5031edbb08fff7f919752d725e2654c9252&")
    estilo_curso(embed)
    await interaction.response.send_message(embed=embed)


# ================= READY =================

@bot.event
async def on_ready():
    print(f"🔥 Bot conectado como {bot.user}")

    # views persistentes: seguro registrar de novo a cada reconexão (idempotente)
    bot.add_view(TicketView())
    bot.add_view(ConfirmarOuFecharView())
    bot.add_view(PainelAdminView())
    bot.add_view(ViewInscricao())
    bot.add_view(BoletimView())
    bot.add_view(AusenciaView())
    bot.add_view(PainelCursosView())
    with cursos_conn() as conn:
        cursos_salvos = conn.execute("SELECT id, status FROM cursos").fetchall()
    for curso_id, status in cursos_salvos:
        if status != "FINALIZADO":
            bot.add_view(CursoInscricaoView(curso_id))
        bot.add_view(ControleCursoView(curso_id))
    for codigo, registro in carregar_inscricoes().items():
        if isinstance(registro, dict) and registro.get("status") == "pendente":
            bot.add_view(ViewDecisaoInscricao(codigo))

    # o resto (purge, envio de painel, sync de slash commands) só deve
    # rodar UMA vez por processo — repetir isso a cada reconexão soma
    # duplicatas e pode bater em rate limit da API do Discord.
    if bot._ready_sent:
        return
    bot._ready_sent = True

    print(f"Bot: {bot.user} | ID: {bot.user.id}")
    print(f"GUILD CONFIG: {GUILD_ID}")

    guild = discord.utils.get(bot.guilds, id=GUILD_ID)

    if not guild:
        print(f"✅ Guild {GUILD_ID} NÃO encontrada.")
        return

    print(f"<:YES:1540777802935181444> Guild encontrada: {guild.name}")

    if not getattr(bot, "_boletim_task", None) or bot._boletim_task.done():
        bot._boletim_task = bot.loop.create_task(tarefa_limpeza_boletim())

    # ================= PAINEL DE BOLETIM =================
    canal_boletim = guild.get_channel(ID_CANAL_BOLETIM)
    if canal_boletim:
        try:
            async for msg in canal_boletim.history(limit=50):
                if msg.author == bot.user:
                    await msg.delete()

            painel_boletim = discord.Embed(
                title="<:BOLETIM:1541310958964576276> Sistema de Boletim Interno",
                description=(
                    "Clique no botão abaixo para iniciar um boletim.\n\n"
                    "<:111:1540791811310747759> **Observações:**\n\n"
                    "<:ponto:1540777974427553862> O boletim será salvo como rascunho até que seja enviado.\n\n"
                    "<:ponto:1540777974427553862> Você pode editar o boletim antes de enviá-lo.\n\n"
                    "<:ponto:1540777974427553862> Rascunhos ficam disponíveis por `24 horas`.\n\n"
                    "<:ponto:1540777974427553862> Apenas membros com cargos autorizados podem emitir boletins:\n\n"
                    f"<@&{ID_CARGO_P1_BOLETIM}>\n\n"
                    f"<:ponto:1540777974427553862> O boletim será enviado para:\n" 
                    f"<#{CANAL_BOLETINS['9°BPM']}>.\n\n"
                    "<:ponto:1540777974427553862> Qualquer dúvida, solicite ajuda à equipe."
                ),
                color=discord.Color.yellow(),
            )
            painel_boletim.set_image(url="https://cdn.discordapp.com/attachments/1444735189765849320/1540797986068627598/9_bpm_SOLICITAR_FUNCIONAL_.png?ex=6a8b4372&is=6a89f1f2&hm=3817fcf103b86728f40bdc0b34c8836cdd3512202c519fa7714ef18122861fac&")
            painel_boletim.set_thumbnail(url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8c9598&is=6a8b4418&hm=0b9faa95c5cc5c9231eb5090e3ba60d87bbcf067a833b9fe9c655d32bc737a87&")
            painel_boletim.set_footer(text="Batalhão 9° BPM/M Virtual® Todos direitos reservados", icon_url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8c9598&is=6a8b4418&hm=0b9faa95c5cc5c9231eb5090e3ba60d87bbcf067a833b9fe9c655d32bc737a87&")
            await canal_boletim.send(embed=painel_boletim, view=BoletimView())
        except discord.HTTPException as erro:
            print(f"Erro ao enviar painel de boletim: {erro}")

    canal_ausencia = bot.get_channel(CANAL_AUSENCIA_ID)
    if canal_ausencia:
        try:
            await canal_ausencia.purge(limit=5)
            await canal_ausencia.send(embed=embed_painel_ausencia(), view=AusenciaView())
        except discord.HTTPException as erro:
            print(f"Erro ao enviar painel de ausência: {erro}")

    canal_cursos = bot.get_channel(CANAL_PAINEL_CURSOS)
    if canal_cursos:
        try:
            await canal_cursos.purge(limit=5)
            painel_cursos = discord.Embed(
                title="<:CERTIFICADO:1540945192150896740> PAINEL DE CURSOS",
                description=(
                    "<:ponto:1540777974427553862> Utilize o menu abaixo para abrir um novo curso.\n"
                    f"<:ponto:1540777974427553862> Apenas (<@&{CARGOS_INSTRUTOR[0]}>) podem abrir cursos e emitir certificados.\n"
                ),
                color=0xFFFF00,
            )
            painel_cursos.set_image(url=BANNER_CURSO)
            estilo_curso(painel_cursos)
            await canal_cursos.send(embed=painel_cursos, view=PainelCursosView())
        except discord.HTTPException as erro:
            print(f"Erro ao enviar painel de cursos: {erro}")

    # ================= PAINEL SET =================
    try:
        canal = guild.get_channel(CANALETA_SOLICITAR_SET_ID)

        if canal:
            async for msg in canal.history(limit=10):
                if msg.author == bot.user:
                    await msg.delete()

            embed = discord.Embed(
                title=" Sistema de Funcional",
                description=(
                    "Clique no botão abaixo para iniciar sua solicitação.\n\n"
                    "Clique no botão abaixo para alterar **Solicitar sua Funcional**.\n\n"
                    "Regras:\n"
                    f"<:ponto:1540777974427553862> Apenas nomes **REGISTRAVEIS**\n"
                    f"<:ponto:1540777974427553862> Após a solicitação **AGUARDE**\n"
                    f"<:ponto:1540777974427553862> Apenas maiores de 18 anos\n"
                    f"<:ponto:1540777974427553862> Todas as alterações são **registradas**\n\n"
                    f"<:ponto:1540777974427553862> Caso tenha duvidas <#1473875232430227497>\n\n"
                ),
                color=discord.Color.yellow(),
            )
            embed.set_image(url="https://cdn.discordapp.com/attachments/1444735189765849320/1540797986068627598/9_bpm_SOLICITAR_FUNCIONAL_.png?ex=6a8b4372&is=6a89f1f2&hm=3817fcf103b86728f40bdc0b34c8836cdd3512202c519fa7714ef18122861fac&")
            embed.set_thumbnail(
                url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8b4418&is=6a89f298&hm=ccef0422a39e4382dc5e5b9858c859cb3a0dd81a22eac8f643b85ee6fa955c8f&"
            )
            embed.set_footer(icon_url="https://cdn.discordapp.com/attachments/1444735189765849320/1540798683749285998/9_BPM_LOGO.png?ex=6a8b4418&is=6a89f298&hm=ccef0422a39e4382dc5e5b9858c859cb3a0dd81a22eac8f643b85ee6fa955c8f&", text="Batalhão 9° BPM/M Virtual® Todos direitos reservados.")

            await canal.send(embed=embed, view=TicketView())
    except Exception as e:
        print(f"Erro ao enviar painel SET: {e}")

    # ================= PAINEL ADMINISTRATIVO =================
    try:
        await enviar_painel(guild)
    except Exception as e:
        print(f"Erro ao enviar painel administrativo: {e}")

    # ================= SYNC SLASH =================
    try:
        # A sincronização global substitui versões globais antigas pela lista
        # completa de comandos declarada neste arquivo.
        await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        synced = await bot.tree.sync()
        print(f"🔧 Slash Commands globais sincronizados: {[cmd.name for cmd in synced]}")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")

    # ================= LOG DE START =================
    await enviar_log(guild, "🚀 Bot iniciado", "Sistema de SET e Slash Commands ativos.")


# ================= RUN =================

if not TOKEN:
    print("ERRO: TOKEN_ROTA não definido. Coloque TOKEN_ROTA no .env ou variáveis de ambiente.")
else:
    db.init_db()
    bot.run(TOKEN)