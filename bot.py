import discord
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput
from discord import Embed
import asyncio
import os
import aiohttp
import io
from datetime import datetime
from zoneinfo import ZoneInfo
BRASIL = ZoneInfo("America/Sao_Paulo")


intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ============================
# CONFIGURAÇÕES DO SERVIDOR
# ============================
GUILD_ID = 1343398652336537654

VERIFY_CHANNEL_ID = 1343398652349255758
LOG_CHANNEL_ID = 1450001931278745640

ROLE_VERIFY_ID = 1345435302285545652
ROLE_AUTOROLE_ID = 1343645401051431017
ADMIN_ROLE_ID = 1449998328334123208

PAINEL_CHANNEL_ID = 1450968994076033115

# Advertências
ID_CARGO_ADV1 = 1343788657760534619
ID_CARGO_ADV2 = 1343647931743469620
ID_CARGO_ADV3 = 1343648148861489247
ID_CARGO_BANIDO = 1343648181174665228

# Autorizados para comandos (todos os slash commands usarão estes cargos)
CARGOS_AUTORIZADOS = [
    1449985109116715008,
]

# ============================
# TOKEN
# ============================
TOKEN = os.getenv("TOKEN")  # coloque TOKEN no .env

# ============================
# LOGS
# ============================
async def enviar_log_embed(guild: discord.Guild, embed: discord.Embed):
    if not guild:
        return
    canal = guild.get_channel(LOG_CHANNEL_ID)
    if canal:
        try:
            await canal.send(embed=embed)
        except:
            return

async def enviar_log(guild, titulo, descricao, cor=discord.Color.green()):
    canal = guild.get_channel(LOG_CHANNEL_ID) if guild else None
    if canal:
        embed = discord.Embed(title=titulo, description=descricao, color=cor)
        embed.set_footer(text="Sistema de Logs - Tropa do Trevo")
        try:
            await canal.send(embed=embed)
        except:
            pass

# ============================
# PERMISSÕES
# ============================
def has_authorized_role(member: discord.Member) -> bool:
    if not member or not hasattr(member, "roles"):
        return False
    return any(role.id in CARGOS_AUTORIZADOS for role in member.roles)

async def require_authorized(interaction: discord.Interaction) -> bool:
    if not has_authorized_role(interaction.user):
        await interaction.response.send_message("❌ Você não tem permissão.", ephemeral=True)
        return False
    return True

# ============================
# PAINEL ADMIN
# ============================
class PainelAdminView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📜 Ver Logs", style=discord.ButtonStyle.secondary, custom_id="view_logs")
    async def view_logs(self, interaction: discord.Interaction, button: Button):
        admin_role = interaction.guild.get_role(ADMIN_ROLE_ID)
        if admin_role not in interaction.user.roles:
            return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)

        log = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if log:
            await interaction.response.send_message(f"📌 Os logs estão em: {log.mention}", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Canal de logs não encontrado.", ephemeral=True)

async def enviar_painel(guild: discord.Guild):
    if not guild:
        return
    canal = guild.get_channel(PAINEL_CHANNEL_ID)
    if canal:
        try:
            await canal.purge(limit=10)
        except:
            pass
        embed = Embed(title="🛠 Painel Administrativo",
                      description="Gerencie o sistema abaixo:",
                      color=discord.Color.green())
        try:
            await canal.send(embed=embed, view=PainelAdminView())
        except:
            pass

# ============================
#      SISTEMA DE ADVs
# ============================
@bot.tree.command(name="adv", description="Aplica advertência.", guild=discord.Object(id=GUILD_ID))
async def adv(interaction: discord.Interaction, membro: discord.Member, motivo: str):
    if not await require_authorized(interaction):
        return

    # mantém checagem extra: só membros com permissão de kick podem aplicar adv (opcional)
    if not interaction.user.guild_permissions.kick_members:
        return await interaction.response.send_message("❌ Você precisa de permissão para expulsar (kick) para aplicar advertências.", ephemeral=True)

    adv1 = interaction.guild.get_role(ID_CARGO_ADV1)
    adv2 = interaction.guild.get_role(ID_CARGO_ADV2)
    adv3 = interaction.guild.get_role(ID_CARGO_ADV3)
    banido = interaction.guild.get_role(ID_CARGO_BANIDO)

    if banido in membro.roles:
        return await interaction.response.send_message("⚠ Esse membro já está banido.", ephemeral=True)

    if adv3 in membro.roles:
        try:
            await membro.remove_roles(adv3)
            await membro.add_roles(banido)
            msg = "🚫 4ª advertência → BANIDO"
        except Exception:
            return await interaction.response.send_message("❌ Erro ao atualizar cargos.", ephemeral=True)
    elif adv2 in membro.roles:
        await membro.remove_roles(adv2)
        await membro.add_roles(adv3)
        msg = "⚠ 3ª advertência aplicada!"
    elif adv1 in membro.roles:
        await membro.remove_roles(adv1)
        await membro.add_roles(adv2)
        msg = "⚠ 2ª advertência aplicada!"
    else:
        await membro.add_roles(adv1)
        msg = "⚠ 1ª advertência aplicada!"

    await interaction.response.send_message(msg, ephemeral=True)

    # log
    embed = discord.Embed(
        title="⚠ Advertência aplicada",
        description=f"**Membro:** {membro.mention}\n**Por:** {interaction.user.mention}\n**Motivo:** {motivo}",
        color=discord.Color.orange(),
        timestamp=discord.utils.utcnow()
    )
    await enviar_log_embed(interaction.guild, embed)

# ============================
#            BAN
# ============================
@bot.tree.command(name="ban", description="Bane um membro.", guild=discord.Object(id=GUILD_ID))
async def ban(interaction: discord.Interaction, membro: discord.Member, motivo: str):
    if not await require_authorized(interaction):
        return

    # checar permissão de ban
    if not interaction.user.guild_permissions.ban_members:
        return await interaction.response.send_message("❌ Você precisa da permissão de banir.", ephemeral=True)

    try:
        await membro.ban(reason=motivo)
        await interaction.response.send_message(f"🔨 {membro.mention} banido!", ephemeral=True)
    except discord.Forbidden:
        return await interaction.response.send_message("❌ O bot não pode banir esse usuário.", ephemeral=True)

    embed = discord.Embed(
        title="🚫 Membro Banido",
        description=f"**Membro:** {membro.mention}\n**Por:** {interaction.user.mention}\n**Motivo:** {motivo}",
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow()
    )
    await enviar_log_embed(interaction.guild, embed)            

# ============================
# SLASH COMMANDS
# ============================
@bot.tree.command(name="clearall", description="Apaga todas as mensagens do canal atual.", guild=discord.Object(id=GUILD_ID))
async def clearall(interaction: discord.Interaction):
    if not await require_authorized(interaction):
        return
    canal = interaction.channel
    guild = interaction.guild
    if not canal or not guild:
        return await interaction.response.send_message("❌ Contexto inválido.", ephemeral=True)
    await interaction.response.send_message(f"🧹 Limpando todas as mensagens do canal **{canal.name}**...", ephemeral=True)
    try:
        await canal.purge(limit=None)
    except:
        try:
            await canal.purge()
        except:
            pass
    try:
        embed_confirm = Embed(title="🧹 Canal Limpo",
                              description=f"As mensagens do canal `{canal.name}` foram apagadas com sucesso!",
                              color=discord.Color.green())
        await canal.send(embed=embed_confirm)
    except:
        pass
    embed_log = Embed(title="🧹 Log - Canal Limpo",
                      description=(f"**Usuário:** {interaction.user.mention}\n"
                                   f"**ID do usuário:** `{interaction.user.id}`\n"
                                   f"**Canal limpo:** {canal.mention}\n"
                                   f"**Servidor:** `{guild.name}`"),
                      color=discord.Color.orange(),
                      timestamp=discord.utils.utcnow())
    embed_log.set_footer(text=f"Ação: clearall")
    await enviar_log_embed(guild, embed_log)

# ============================
# MODAL /mensagem
# ============================
class MensagemModal(Modal, title="📢 Enviar Mensagem"):
    conteudo = TextInput(label="Conteúdo da mensagem", style=discord.TextStyle.paragraph, required=True, max_length=2000)
    async def on_submit(self, interaction: discord.Interaction):
        if not has_authorized_role(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
            return
        await interaction.response.send_message("⏳ Enviando...", ephemeral=True)
        try:
            msg_inicial = await interaction.channel.send(self.conteudo.value)
        except:
            await interaction.followup.send("❌ Não consegui enviar a mensagem.", ephemeral=True)
            return
        await interaction.followup.send("📎 Responda aquela mensagem com anexos em até 5 minutos.", ephemeral=True)
        def check(m: discord.Message):
            return m.reference and m.reference.message_id == msg_inicial.id and m.author == interaction.user
        try:
            reply = await bot.wait_for("message", timeout=300.0, check=check)
            files = []
            async with aiohttp.ClientSession() as session:
                for a in reply.attachments:
                    try:
                        async with session.get(a.url) as resp:
                            dados = await resp.read()
                            files.append(discord.File(io.BytesIO(dados), filename=a.filename))
                    except:
                        continue
            try:
                await msg_inicial.delete()
                await reply.delete()
            except:
                pass
            try:
                await interaction.channel.send(content=self.conteudo.value, files=files)
            except:
                await interaction.followup.send("❌ Não consegui reenviar a mensagem.", ephemeral=True)
        except asyncio.TimeoutError:
            try:
                await interaction.followup.send("⏰ Tempo esgotado. Nenhum anexo recebido.", ephemeral=True)
            except:
                pass

@bot.tree.command(name="mensagem", description="Enviar mensagem como o bot.", guild=discord.Object(id=GUILD_ID))
async def mensagem(interaction: discord.Interaction):
    if not await require_authorized(interaction):
        return
    await interaction.response.send_modal(MensagemModal())

# ============================
# SISTEMA ROTA TICKET + PATENTES
# ============================
solicitacoes_abertas = {}

PATENTES_ROTA = {
    "[❯] Soldado de 1º Classe PM": 1343408322774175785,
    "[❯❯] Cabo PM": 1343408303417331772,
    "[❯❯❯] 3º Sargento PM": 1343404402219814932,
    "[❯ ❯❯❯] 2º Sargento PM": 1343408106457272462,
    "[❯❯ ❯❯❯] 1º Sargento PM": 1343408155161264158,
    "[△] Sub-Tenente PM": 1343727303795933184,
    "[✯] Aspirante a Oficial PM": 1343648749381091570,
    "[✧] 2º Tenente PM": 1343419697294479471,
    "[✧✧] 1º Tenente PM": 1343408376302014495,
    "[✧✧✧] Capitão PM": 1343404318946103346,
    "[✵✧✧] Major PM": 1343401976523784253,
    "[✵✵✧] Tenente Coronel PM": 1343401212417937468,
}

CANALETA_SOLICITAR_SET_ID = 1343398652349255758
CARGO_NOVATO_ID = 1345435302285545652
CATEGORIA_TICKET_ID = 1343398652349255757
CANAL_LOGS_ROTA = 1473844393893953679
CARGO_ROTA_ID = 1343645401051431017

solicitacoes_abertas = {}

# ================= TICKET VIEW =================

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Solicitar Funcional",
        style=discord.ButtonStyle.secondary,
        custom_id="rota_solicitar_funcional"
    )
    async def abrir_ticket(self, interaction: discord.Interaction, button: Button):

        if interaction.user.id in solicitacoes_abertas:
            await interaction.response.send_message(
                "⚠️ Você já possui um ticket aberto.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        user = interaction.user
        category = guild.get_channel(CATEGORIA_TICKET_ID)

        if not category:
            await interaction.followup.send(
                "❌ Categoria de ticket não encontrada.",
                ephemeral=True
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        canal = await guild.create_text_channel(
            name=f"ticket-rota-{user.name}",
            category=category,
            overwrites=overwrites
        )

        solicitacoes_abertas[user.id] = {
            "canal_id": canal.id
        }

        view = View(timeout=None)
        view.add_item(SelectPatente(user.id))

        await canal.send(
            f"{user.mention}, selecione sua patente:",
            view=view
        )

        await interaction.followup.send(
            "🎟️ Ticket criado com sucesso.",
            ephemeral=True
        )

# ================= SELECT PATENTE =================

class SelectPatente(Select):
    def __init__(self, user_id):
        self.user_id = user_id

        options = [
            discord.SelectOption(label=nome, value=nome)
            for nome in PATENTES_ROTA
        ]

        super().__init__(
            placeholder="Escolha sua patente",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        await interaction.response.send_modal(
            DadosPessoaisModal(
                self.user_id,
                self.values[0],
                PATENTES_ROTA[self.values[0]]
            )
        )

# ================= MODAL =================

class DadosPessoaisModal(Modal, title="Dados ROTA"):

    nome = TextInput(
        label="Nome Completo",
        required=True,
        max_length=80
    )

    passaporte = TextInput(
        label="Passaporte",
        required=True,
        max_length=20
    )

    def __init__(self, user_id, patente_nome, patente_id):
        super().__init__()
        self.user_id = user_id
        self.patente_nome = patente_nome
        self.patente_id = patente_id

    async def on_submit(self, interaction: discord.Interaction):

        if self.user_id not in solicitacoes_abertas:
            await interaction.response.send_message(
                "❌ Ticket não encontrado.",
                ephemeral=True
            )
            return

        solicitacoes_abertas[self.user_id].update({
            "patente_id": self.patente_id,
            "nome": self.nome.value.strip(),
            "passaporte": self.passaporte.value.strip()
        })

        embed = Embed(
            title="Solicitação Funcional.",
            description=(
                f"**Solicitante:** {interaction.user.mention}\n"
                f"**Nome:** {self.nome.value.strip()}\n"
                f"**Passaporte:** {self.passaporte.value.strip()}\n"
                f"**Companhia:** 1° BPCHQ ROTA\n"
                f"**Patente:** {self.patente_nome}"
            ),
            color=discord.Color.dark_gray()
        )

        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/1444735189765849320/1473870387547734139/032.png"
        )

        embed.set_image(
            url="https://jpimg.com.br/uploads/2017/08/SIG20170823031.jpg"
        )

        embed.set_footer(
            text="Batalhão Rota Virtual® Todos direitos reservados."
        )

        canal_logs = await interaction.client.fetch_channel(CANAL_LOGS_ROTA)

        await canal_logs.send(
            embed=embed,
            view=ConfirmarOuFecharView(self.user_id)
        )

        await interaction.response.send_message(
            "✅ Solicitação enviada para avaliação.",
            ephemeral=True
        )

# ================= CONFIRMAR / CANCELAR =================

class ConfirmarOuFecharView(View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(
        label="✅ Confirmar SET",
        style=discord.ButtonStyle.success,
        custom_id="confirmar_set"
    )
    async def confirmar(self, interaction: discord.Interaction, button: Button):

        dados = solicitacoes_abertas.pop(self.user_id, None)

        if not dados:
            await interaction.response.send_message(
                "❌ Solicitação não encontrada.",
                ephemeral=True
            )
            return

        membro = interaction.guild.get_member(self.user_id)

        novo_apelido = f"#{dados['passaporte']} | {dados['nome']}"

        try:
            await membro.edit(nick=novo_apelido)
        except:
            pass

        novato = interaction.guild.get_role(CARGO_NOVATO_ID)

        if novato in membro.roles:
            await membro.remove_roles(novato)

        await membro.add_roles(
            interaction.guild.get_role(dados['patente_id']),
            interaction.guild.get_role(CARGO_ROTA_ID)
        )

        agora = datetime.now(BRASIL).strftime("%d/%m/%Y às %H:%M")

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()

        embed.description += (
            f"\n\n✅ **Aprovado por:** {interaction.user.mention}"
            f"\n📌 **ID do aprovador:** `{interaction.user.id}`"
            f"\n🕒 **Data:** {agora}"
        )

        await interaction.message.edit(embed=embed, view=None)

        await interaction.response.send_message(
            "✅ SET confirmado.",
            ephemeral=True
        )

        canal = interaction.guild.get_channel(dados["canal_id"])

        if canal:
            await asyncio.sleep(5)
            await canal.delete()


    @discord.ui.button(
        label="❌ Cancelar",
        style=discord.ButtonStyle.danger,
        custom_id="cancelar_set"
    )
    async def cancelar(self, interaction: discord.Interaction, button: Button):

        await interaction.response.send_modal(
            CancelarModal(self.user_id)
        )

# ================= CANCELAR =================

class CancelarModal(Modal, title="Cancelar Solicitação"):

    motivo = TextInput(
        label="Informe o motivo do cancelamento",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):

        dados = solicitacoes_abertas.pop(self.user_id, None)

        if not dados:
            await interaction.response.send_message(
                "❌ Solicitação não encontrada.",
                ephemeral=True
            )
            return

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()

        embed.description += (
            f"\n\n❌ **Cancelado por:** {interaction.user.mention}"
            f"\n📌 **ID do avaliador:** `{interaction.user.id}`"
            f"\n📝 **Motivo:** {self.motivo.value}"
        )

        await interaction.message.edit(embed=embed, view=None)

        membro = interaction.guild.get_member(self.user_id)

        if membro:
            try:
                await membro.send(
                    f"🚫 Sua solicitação foi cancelada.\n\n"
                    f"Motivo:\n{self.motivo.value}"
                )
            except:
                pass

        await interaction.response.send_message(
            "❌ Solicitação cancelada.",
            ephemeral=True
        )

        canal = interaction.guild.get_channel(dados["canal_id"])

        if canal:
            await asyncio.sleep(5)
            await canal.delete()

# ============================
# READY
# ============================
@bot.event
async def on_ready():
    print(f"🔥 Bot conectado como {bot.user}")

    # Persistir botões (evita interação falhar depois de um tempo)
    bot.add_view(TicketView())
    bot.add_view(PainelAdminView())

    guild = bot.get_guild(GUILD_ID)
    if not guild:
        print("⚠️ Servidor não encontrado!")
        return

    await enviar_log(guild, "🚀 Bot iniciado", "Sistema de SET e Slash Commands ativos.")

    # PAINEL SET
    try:
        canal = guild.get_channel(CANALETA_SOLICITAR_SET_ID)
        if canal:
            async for msg in canal.history(limit=10):
                if msg.author == bot.user:
                    await msg.delete()

            embed = Embed(
                title="ROTA | Solicitar Funcional",
                description=(
                    "Clique no botão abaixo para iniciar sua solicitação.\n\n"
                    "Regras:\n\n"
                    "• Apenas nomes **REGISTRAVEIS**\n"
                    "• Após a solicitação **AGUARDE**\n"
                    "• Apenas maiores de 18 anos\n\n"
                    "Qualquer duvida chamar <#1473875232430227497>\n\n"
                    "_Dignidade acima de tudo_\n"
                    "_A Rota é reservada aos heróis_\n"
                ),
                color=discord.Color.dark_gray()
            )

            embed.set_thumbnail(
                url="https://cdn.discordapp.com/attachments/1444735189765849320/1473870387547734139/032.png"
            )
            embed.set_image(
                url="https://cdn.discordapp.com/attachments/1444735189765849320/1473872047947120640/54-anos-de-Rota.jpg"
            )
            embed.set_footer(text="Batalhão Rota Virtual® Todos direitos reservados.")

            await canal.send(embed=embed, view=TicketView())

    except Exception as e:
        print(f"Erro ao enviar painel SET: {e}")

    bot.add_view(TicketView())
    bot.add_view(PainelAdminView())
    bot.add_view(ConfirmarOuFecharView(0))



# ============================
# RUN
# ============================
if not TOKEN:
    print("ERRO: TOKEN não definido.")
else:
    bot.run(TOKEN)

