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
        # Verificamos que el usuario siga en el canal y tenga permisos
        if interaction.user.voice and interaction.user.voice.channel.permissions_for(interaction.user).manage_channels:
            await interaction.user.voice.channel.edit(name=f"🎙️ {self.nombre_sala.value}")
            await interaction.response.send_message(f"✅ Canal renombrado a: **{self.nombre_sala.value}**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No tienes permiso para editar este canal o no estás en él.", ephemeral=True)

class ControlPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) 
        
    @discord.ui.button(
        label="Hacer Invisible",
        emoji="👻", 
        style=discord.ButtonStyle.secondary,
        custom_id="btn_invisible_toggle"
    )
    async def toggle_phantom_mode(self, interaction: discord.Interaction, button: discord.Button):
        pass

    @discord.ui.button(label="Cambiar Nombre", style=discord.ButtonStyle.primary, custom_id="rename_btn")
    async def rename_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Solo el que tiene permiso de gestionar canales puede usar el botón
        if interaction.user.voice and interaction.user.voice.channel.permissions_for(interaction.user).manage_channels:
            await interaction.response.send_modal(ConfigModal())
        else:
            await interaction.response.send_message("⚠️ Solo el administrador de la sala puede cambiar el nombre.", ephemeral=True)

    @discord.ui.button(label="🔒 Privado / 🔓 Público", style=discord.ButtonStyle.secondary, custom_id="toggle_privacy")
    async def privacy_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.voice or not interaction.user.voice.channel.permissions_for(interaction.user).manage_permissions:
            return await interaction.response.send_message("⚠️ No tienes permisos para cambiar la privacidad.", ephemeral=True)

        channel = interaction.user.voice.channel
        overwrites = channel.overwrites_for(interaction.guild.default_role)
        
        # Invertimos el permiso de conectar
        overwrites.connect = not overwrites.connect
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrites)
        
        estado = "🔓 **PÚBLICO**" if overwrites.connect else "🔒 **PRIVADO**"
        await interaction.response.send_message(f"La sala ahora es {estado}", ephemeral=True)
    
    @discord.ui.button(label="👻 Hacer Invisible", style=discord.ButtonStyle.secondary, custom_id="toggle_visible")
    async def visible_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 1. Verificamos que el usuario sea el dueño (tenga permisos de gestión)
        if not interaction.user.voice or not interaction.user.voice.channel.permissions_for(interaction.user).manage_channels:
            return await interaction.response.send_message("❌ Solo el dueño puede ocultar esta sala.", ephemeral=True)

        channel = interaction.user.voice.channel
        overwrites = channel.overwrites_for(interaction.guild.default_role)
        
        # 2. Alternamos el permiso de VER el canal
        # Si view_channel es None o True, lo ponemos en False (Invisible)
        # Si ya es False, lo ponemos en True (Visible)
        nuevo_estado = not overwrites.view_channel if overwrites.view_channel is not None else False
        overwrites.view_channel = nuevo_estado
        
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrites)
        
        estado_txt = "🔓 **VISIBLE**" if nuevo_estado else "👻 **INVISIBLE**"
        await interaction.response.send_message(f"La sala ahora es {estado_txt} para el resto del servidor.", ephemeral=True)

        # ESTAS LÍNEAS DEBEN LLEVAR LOS MISMOS ESPACIOS QUE EL 'IF' ARRIBA:
        await channel.set_permissions(everyone_role, overwrite=current_overwrites)
        await interaction.message.edit(view=self)
        await interaction.response.send_message(f"La sala {nuevo_estado}", ephemeral=True)

# --- EVENTOS DEL BOT ---

@bot.event
async def on_ready():
    bot.add_view(ControlPanel()) 
    print(f"✅ EclipseBot conectado como {bot.user}")

@bot.event
async def on_voice_state_update(member, before, after):
    ID_CanalCreador = 148930088
    # 1. LÓGICA DE CREACIÓN (Solo para el Dueño)
    if after.channel and after.channel.id == ID_CanalCreador:
        guild = member.guild
        category = after.channel.category
        
        # PERMISOS: Solo el creador tiene 'manage_channels' y 'manage_permissions'
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=True), # Público por defecto
            member: discord.PermissionOverwrite(
                manage_channels=True, 
                manage_permissions=True, # Solo él puede usar los botones y el engranaje
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

        # Mensaje de bienvenida con el Panel
        await new_channel.send(
            content=f"👑 **{member.mention}**, eres el dueño de esta sala.\nSolo tú puedes usar estos botones para configurarla.",
            view=ControlPanel()
        )

    # 2. LÓGICA DE LIMPIEZA
    if before.channel:
        # Detectamos canales creados por el bot para borrar si están vacíos
        if ("Sala de" in before.channel.name or "🎙️" in before.channel.name) and len(before.channel.members) == 0:
            # Evitamos borrar el canal generador por error
            if before.channel.id != ID_CanalCreador:
                try:
                    await before.channel.delete()
                    print(f"🗑️ Limpieza: Canal {before.channel.name} eliminado.")
                except discord.NotFound:
                    pass
                except Exception as e:
                    print(f"❌ Error al borrar: {e}")

bot.run(config.TOKEN)