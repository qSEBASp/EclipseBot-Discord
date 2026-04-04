import discord
from discord.ext import commands
import config

intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.message_content = True 

bot = commands.Bot(command_prefix="!", intents=intents)

# --- INTERFAZ DE USUARIO (MODALES Y BOTONES) ---

class ConfigModal(discord.ui.Modal, title="Configura tu Sala"):
    nombre_sala = discord.ui.TextInput(
        label="Nuevo nombre del canal", 
        placeholder="Ej: Entrenamiento Alpha ⚔️", 
        min_length=3, 
        max_length=25
    )

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.voice and interaction.user.voice.channel.permissions_for(interaction.user).manage_channels:
            await interaction.user.voice.channel.edit(name=f"🎙️ {self.nombre_sala.value}")
            await interaction.response.send_message(f"✅ Canal renombrado a: **{self.nombre_sala.value}**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No tienes permiso para editar este canal o no estás en él.", ephemeral=True)

class ControlPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) 
        
    @discord.ui.button(label="Cambiar Nombre", style=discord.ButtonStyle.primary, custom_id="rename_btn")
    async def rename_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.voice and interaction.user.voice.channel.permissions_for(interaction.user).manage_channels:
            await interaction.response.send_modal(ConfigModal())
        else:
            await interaction.response.send_message("⚠️ Solo el administrador de la sala puede cambiar el nombre.", ephemeral=True)

    @discord.ui.button(label="🔒 Privado / 🔓 Público", style=discord.ButtonStyle.secondary, custom_id="toggle_privacy")
    async def privacy_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.voice or not interaction.user.voice.channel.permissions_for(interaction.user).manage_permissions:
            return await interaction.response.send_message("⚠️ No tienes permisos para cambiar la privacidad.", ephemeral=True)
        
        channel = interaction.user.voice.channel
        everyone_role = interaction.guild.default_role
        overwrites = channel.overwrites_for(everyone_role)
        
        overwrites.connect = not overwrites.connect
        await channel.set_permissions(everyone_role, overwrite=overwrites)
        
        estado = "🔓 **PÚBLICO**" if overwrites.connect else "🔒 **PRIVADO**"
        await interaction.response.send_message(f"La sala ahora es {estado}", ephemeral=True)
        
    @discord.ui.button(label="👻 Hacer Invisible", style=discord.ButtonStyle.secondary, custom_id="toggle_visible")
    async def visible_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.voice or not interaction.user.voice.channel.permissions_for(interaction.user).manage_channels:
            return await interaction.response.send_message("❌ No eres el dueño de esta sala.", ephemeral=True)

        channel = interaction.user.voice.channel
        everyone_role = interaction.guild.default_role
        overwrites = channel.overwrites_for(everyone_role)
        
        nuevo_estado = not overwrites.view_channel if overwrites.view_channel is not None else False
        overwrites.view_channel = nuevo_estado
        
        await channel.set_permissions(everyone_role, overwrite=overwrites)
        
        estado_txt = "🔓 **VISIBLE**" if nuevo_estado else "👻 **INVISIBLE**"
        await interaction.response.send_message(f"La sala ahora es {estado_txt}", ephemeral=True)

# --- EVENTOS DEL BOT ---

@bot.event
async def on_ready():
    bot.add_view(ControlPanel()) 
    print(f"✅ EclipseBot conectado como {bot.user}")

@bot.event
async def on_voice_state_update(member, before, after):
    ID_CanalCreador = 148930088 # Asegúrate de que este ID sea el correcto en tu server
    
    if after.channel and after.channel.id == ID_CanalCreador:
        guild = member.guild
        category = after.channel.category
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=True),
            member: discord.PermissionOverwrite(
                manage_channels=True, 
                manage_permissions=True,
                move_members=True, 
                connect=True,
                view_channel=True
            )
        }
        
        new_channel = await guild.create_voice_channel(
            name=f"🎙️ Sala de {member.display_name}",
            category=category,
            overwrites=overwrites
        )
        
        await member.move_to(new_channel)

        await new_channel.send(
            content=f"👑 **{member.mention}**, eres el dueño de esta sala.\nSolo tú puedes usar estos botones para configurarla.",
            view=ControlPanel()
        )

    if before.channel:
        if ("Sala de" in before.channel.name or "🎙️" in before.channel.name) and len(before.channel.members) == 0:
            if before.channel.id != ID_CanalCreador:
                try:
                    await before.channel.delete()
                    print(f"🗑️ Limpieza: Canal {before.channel.name} eliminado.")
                except:
                    pass

bot.run(config.TOKEN)