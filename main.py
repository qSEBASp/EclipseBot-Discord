import discord
from discord.ext import commands
import secrets

intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.message_content = True 

bot = commands.Bot(command_prefix="!", intents=intents)

# --- INTERFAZ DE USUARIO (MODALES Y BOTONES) ---

class ConfigModal(discord.ui.Modal, title="Configura tu Sala"):
    nombre_sala = discord.ui.TextInput(
        label="Nuevo nombre del canal", 
        placeholder="Ej: Chill con amigos", 
        min_length=3, 
        max_length=20
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Eliminamos la validación de "Sala de" para que puedan renombrarlo varias veces
        if interaction.user.voice:
            # Editamos el canal de voz actual del usuario
            await interaction.user.voice.channel.edit(name=f"🎙️ {self.nombre_sala.value}")
            await interaction.response.send_message(f"✅ Canal renombrado a: **{self.nombre_sala.value}**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No estás en un canal de voz.", ephemeral=True)

class ControlPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Los botones no caducan

    @discord.ui.button(label="Cambiar Nombre", style=discord.ButtonStyle.primary, custom_id="rename_btn")
    async def rename_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ConfigModal())

    @discord.ui.button(label="🔒 Privado / 🔓 Público", style=discord.ButtonStyle.secondary, custom_id="toggle_privacy")
    async def privacy_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.user.voice.channel
        overwrites = channel.overwrites_for(interaction.guild.default_role)
        
        # Alternamos el permiso de conectar para @everyone
        overwrites.connect = not overwrites.connect
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrites)
        
        estado = "🔓 **PÚBLICO**" if overwrites.connect else "🔒 **PRIVADO**"
        await interaction.response.send_message(f"La sala ahora es {estado}", ephemeral=True)

# --- EVENTOS DEL BOT ---

@bot.event
async def on_ready():
    # Mantiene los botones activos tras reiniciar el bot
    bot.add_view(ControlPanel())
    print(f"✅ Bot conectado como {bot.user}")

@bot.event
async def on_voice_state_update(member, before, after):
    ID_CanalCreador = 1485459503855177820 # Tu ID de canal
    
    # 1. LÓGICA DE CREACIÓN
    if after.channel and after.channel.id == ID_CanalCreador:
        guild = member.guild
        category = after.channel.category
        
        # Permisos para el creador
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=True),
            member: discord.PermissionOverwrite(manage_channels=True, move_members=True, manage_permissions=True)
        }
        
        new_channel = await guild.create_voice_channel(
            name=f"🎙️ Sala de {member.name}",
            category=category,
            overwrites=overwrites
        )
        
        await member.move_to(new_channel)

        # Enviamos el panel de control al nuevo canal
        await new_channel.send(
            content=f"👋 ¡Hola {member.mention}! Usa este panel para personalizar tu sala.",
            view=ControlPanel()
        )

    # 2. LÓGICA DE LIMPIEZA
    if before.channel:
        # Verificamos si el canal está vacío
        # Usamos el emoji para identificarlo aunque le cambien el nombre
        if len(before.channel.members) == 0 and ("Sala de" in before.channel.name or "🎙️" in before.channel.name):
            try:
                await before.channel.delete()
                print(f"🗑️ Canal {before.channel.name} eliminado.")
            except discord.Forbidden:
                print("❌ No tengo permisos para borrar canales.")
            except discord.NotFound:
                pass

bot.run(secrets.TOKEN)