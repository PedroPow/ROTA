import discord
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput
from discord import Embed
import asyncio
import os
import aiohttp
import io
from datetime import datetime   

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ============================
#   CONFIGURAÇÕES DO SERVIDOR
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
#         BOT + INTENTS
# ============================
TOKEN = os.getenv("TOKEN")  # coloque TOKEN no .env

# guard para não reenviar painel/verify em reconexões
bot._ready_sent = False

# ============================
#        SISTEMA DE LOGS
# ============================
async def enviar_log_embed(guild: discord.Guild, embed: discord.Embed):
    if not guild:
        return
    canal = guild.get_channel(LOG_CHANNEL_ID)
    if canal:
        try:
            await canal.send(embed=embed)
        except Exception:
            return

async def enviar_log(guild, titulo, descricao, cor=discord.Color.green()):
    canal = guild.get_channel(LOG_CHANNEL_ID) if guild else None
    if canal:
        embed = discord.Embed(title=titulo, description=descricao, color=cor)
        embed.set_footer(text="Sistema de Logs - Tropa do Trevo")
        try:
            await canal.send(embed=embed)
        except Exception:
            pass

# ============================
#  HELPERS DE PERMISSÃO
# ============================
def has_authorized_role(member: discord.Member) -> bool:
    if not member or not hasattr(member, "roles"):
        return False
    return any(role.id in CARGOS_AUTORIZADOS for role in member.roles)

async def require_authorized(interaction: discord.Interaction) -> bool:
    if not has_authorized_role(interaction.user):
        await interaction.response.send_message("❌ Você não tem permissão (cargo inválido).", ephemeral=True)
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
        except Exception:
            pass
        embed = discord.Embed(
            title="🛠 Painel Administrativo",
            description="Gerencie o sistema abaixo:",
            color=discord.Color.green()
        )
        try:
            await canal.send(embed=embed, view=PainelAdminView())
        except Exception:
            pass

# ============================
#        COMANDO /clearall
# ============================
@bot.tree.command(name="clearall", description="Apaga todas as mensagens do canal atual.", guild=discord.Object(id=GUILD_ID))
async def clearall(interaction: discord.Interaction):
    if not await require_authorized(interaction):
        return

    canal = interaction.channel
    guild = interaction.guild
    if canal is None or guild is None:
        return await interaction.response.send_message("❌ Contexto inválido.", ephemeral=True)

    await interaction.response.send_message(f"🧹 Limpando todas as mensagens do canal **{canal.name}**...", ephemeral=True)

    try:
        await canal.purge(limit=None)
    except Exception:
        try:
            await canal.purge()
        except Exception:
            pass

    try:
        embed_confirm = discord.Embed(
            title="🧹 Canal Limpo",
            description=f"As mensagens do canal `{canal.name}` foram apagadas com sucesso!",
            color=discord.Color.green()
        )
        await canal.send(embed=embed_confirm)
    except Exception:
        pass

    embed_log = discord.Embed(
        title="🧹 Log - Canal Limpo",
        description=(
            f"**Usuário:** {interaction.user.mention}\n"
            f"**ID do usuário:** `{interaction.user.id}`\n"
            f"**Canal limpo:** {canal.mention}\n"
            f"**Servidor:** `{guild.name}`"
        ),
        color=discord.Color.orange(),
        timestamp=discord.utils.utcnow()
    )
    embed_log.set_footer(text=f"Ação: clearall")

    await enviar_log_embed(guild, embed_log)

# ============================
#         MODAL /mensagem
# ============================
class MensagemModal(Modal, title="📢 Enviar Mensagem"):
    conteudo = TextInput(
        label="Conteúdo da mensagem",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):
        if not has_authorized_role(interaction.user):
            await interaction.response.send_message("❌ Você não tem permissão para usar este modal.", ephemeral=True)
            return

        await interaction.response.send_message("⏳ Enviando...", ephemeral=True)

        try:
            msg_inicial = await interaction.channel.send(self.conteudo.value)
        except Exception:
            await interaction.followup.send("❌ Não consegui enviar a mensagem inicial (permissão).", ephemeral=True)
            return

        await interaction.followup.send(
            "📎 Responda aquela mensagem com anexos em até 5 minutos.",
            ephemeral=True
        )

        def check(m: discord.Message):
            return (
                m.reference and
                m.reference.message_id == msg_inicial.id and
                m.author == interaction.user and
                m.channel == interaction.channel
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
                await interaction.followup.send("❌ Não consegui reenviar a mensagem (permissão).", ephemeral=True)

        except asyncio.TimeoutError:
            try:
                await interaction.followup.send("⏰ Tempo esgotado. Nenhum anexo recebido.", ephemeral=True)
            except Exception:
                pass

@bot.tree.command(name="mensagem", description="Enviar mensagem como o bot.", guild=discord.Object(id=GUILD_ID))
async def mensagem(interaction: discord.Interaction):
    if not await require_authorized(interaction):
        return
    await interaction.response.send_modal(MensagemModal())

# ============================
#      SISTEMA DE ADVs
# ============================
@bot.tree.command(name="adv", description="Aplica advertência.", guild=discord.Object(id=GUILD_ID))
async def adv(interaction: discord.Interaction, membro: discord.Member, motivo: str):
    if not await require_authorized(interaction):
        return

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
            msg = "🚫 3ª advertência → BANIDO"
        except Exception:
            return await interaction.response.send_message("❌ Erro ao atualizar cargos.", ephemeral=True)
    elif adv2 in membro.roles:
        await membro.remove_roles(adv2)
        await membro.add_roles(adv3)
        msg = "⚠ 2ª advertência aplicada!"
    elif adv1 in membro.roles:
        await membro.remove_roles(adv1)
        await membro.add_roles(adv2)
        msg = "⚠ 1ª advertência aplicada!"
    else:
        await membro.add_roles(adv1)
        msg = "⚠ advertência verbal aplicada!"

    await interaction.response.send_message(msg, ephemeral=True)

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

# ================= CONFIG =================

TOKEN = os.getenv("TOKEN")

CANALETA_SOLICITAR_SET_ID = 1343398652349255758
CARGO_NOVATO_ID = 1345435302285545652
CATEGORIA_TICKET_ID = 1343398652349255757

CANAL_LOGS_ROTA = 1473844393893953679
CARGO_ROTA_ID = 1343645401051431017

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

solicitacoes_abertas = {}

# ================= TICKET =================

class TicketView(View):
    @discord.ui.button(
        label="Solicitar Funcional",
        style=discord.ButtonStyle.secondary,
        custom_id="rota_solicitar_funcional"
    )
    async def abrir_ticket(self, interaction: discord.Interaction, button: Button):

        if interaction.user.id in solicitacoes_abertas:
            await interaction.response.send_message("⚠️ Você já possui um ticket aberto.", ephemeral=True)
            return

        # ✅ Defer para evitar interaction failed
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        user = interaction.user
        category = guild.get_channel(CATEGORIA_TICKET_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        canal = await guild.create_text_channel(
            name=f"ticket-rota-{user.name}",
            category=category,
            overwrites=overwrites
        )

        solicitacoes_abertas[user.id] = {"canal_id": canal.id}

        view = View()
        view.add_item(SelectPatente(user.id, custom_id=f"select_patente_{user.id}"))

        await canal.send(f"{user.mention}, selecione sua patente:", view=view)
        await interaction.followup.send("🎟️ Ticket criado!", ephemeral=True)

# ================= SELECT PATENTE =================

class SelectPatente(Select):
    def __init__(self, user_id, custom_id):
        self.user_id = user_id
        options = [discord.SelectOption(label=nome, value=nome) for nome in PATENTES_ROTA]
        super().__init__(
            placeholder="Escolha sua patente",
            options=options,
            custom_id=custom_id
        )

    async def callback(self, interaction: discord.Interaction):
        patente_nome = self.values[0]
        patente_id = PATENTES_ROTA[patente_nome]

        await interaction.response.send_modal(
            DadosPessoaisModal(self.user_id, patente_nome, patente_id)
        )

# ================= MODAL =================

class DadosPessoaisModal(Modal, title="Dados ROTA"):
    nome = TextInput(label="Nome Completo", required=True, max_length=80)
    passaporte = TextInput(label="Passaporte", required=True, max_length=20)

    def __init__(self, user_id, patente_nome, patente_id):
        super().__init__()
        self.user_id = user_id
        self.patente_nome = patente_nome
        self.patente_id = patente_id

    async def on_submit(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        nome = self.nome.value.strip()
        passaporte = self.passaporte.value.strip()

        solicitacoes_abertas[self.user_id].update({
            "patente_id": self.patente_id,
            "nome": nome,
            "passaporte": passaporte
        })

        embed = Embed(
            title="Solicitação Funcional.",
            description=(
                f"**Solicitante:** {interaction.user.mention}\n"
                f"**Nome:** {nome}\n"
                f"**Passaporte:** {passaporte}\n"
                f"**Companhia:** 1° BPCHQ ROTA\n"
                f"**Patente:** {self.patente_nome}"
            ),
            color=discord.Color.dark_gray()
        )

        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1444735189765849320/1473870387547734139/032.png?ex=6997c843&is=699676c3&hm=d139e7716d0fb12c5b22c16b9c3114a7a4a149464c7273662875cedc624ee3de&")
        embed.set_image(url="https://jpimg.com.br/uploads/2017/08/SIG20170823031.jpg")
        embed.set_footer(text="Batalhão Rota Virtual® Todos direitos reservados.")

        canal_logs = await interaction.client.fetch_channel(CANAL_LOGS_ROTA)
        await canal_logs.send(embed=embed, view=ConfirmarOuFecharView(self.user_id))

        await interaction.followup.send("✅ Solicitação enviada para avaliação.", ephemeral=True)

# ================= CONFIRMAR =================

class ConfirmarOuFecharView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(
        label="✅ Confirmar SET",
        style=discord.ButtonStyle.success,
        custom_id="confirmar_set"
    )
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        dados = solicitacoes_abertas.pop(self.user_id, None)

        if not dados:
            await interaction.response.send_message("❌ Solicitação não encontrada.", ephemeral=True)
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

        await interaction.response.send_message("✅ SET confirmado e cargos atribuídos.", ephemeral=True)

        await membro.add_roles(
            interaction.guild.get_role(dados['patente_id']),
            interaction.guild.get_role(CARGO_ROTA_ID)
        )

        await interaction.response.send_message("✅ SET confirmado e cargos atribuídos.", ephemeral=True)

# ====================== INÍCIO ======================

@bot.event
async def on_ready():
    if bot._ready_sent:
        return
    bot._ready_sent = True

    guild = bot.get_guild(GUILD_ID)
    if guild:
        await enviar_painel(guild)
        print(f"Bot online em {guild.name} ({guild.id})")

bot.run(TOKEN)
