import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord import app_commands
from discord.ext import commands

# --- WEBSERVER A RENDER SZÁMÁRA ---
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"A Discord Bot elindult es fut!")

    def log_message(self, format, *args):
        # Kiszuri a felesleges HTTP logokat a konzolbol
        return

def run_dummy_server():
    # A Render automatikusan atadja a PORT kornyezeti valtozot (altalaban 10000)
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DummyServer)
    print(f"Webserver elinditva a 0.0.0.0:{port} porton")
    server.serve_forever()

# Azonnal elinditjuk a webservert a hatterszalban
threading.Thread(target=run_dummy_server, daemon=True).start()

# --- DISCORD BOT BEÁLLÍTÁSOK ---
TOKEN = os.environ.get("DISCORD_TOKEN")

EVENT_CONFIG = {
    "Mino run": {"type": "Run", "limit": 4},
    "Féreg run": {"type": "Run", "limit": 4},
    "Kenta run": {"type": "Run", "limit": 4},
    "Menedék expo": {"type": "Expedíció", "limit": 5},
    "Ork Expo": {"type": "Expedíció", "limit": 5},
    "Sivatag Expo": {"type": "Expedíció", "limit": 5},
    "Klán Zállítás": {"type": "Klán Zászló", "limit": None}
}

class EventBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

bot = EventBot()

class EventView(discord.ui.View):
    def __init__(self, creator: discord.Member, event_name: str):
        super().__init__(timeout=None)
        self.creator = creator
        self.event_name = event_name
        self.participants = [creator]
        self.config = EVENT_CONFIG[event_name]
        self.add_item(EventSelect())

    def build_embed(self) -> discord.Embed:
        limit_text = "Nincs korlát" if self.config["limit"] is None else f"{len(self.participants)}/{self.config['limit']}"
        
        embed = discord.Embed(
            title=f"⚔ Esemény: {self.event_name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Szervező", value=self.creator.mention, inline=True)
        embed.add_field(name="Kategória", value=self.config["type"], inline=True)
        embed.add_field(name="Létszám", value=limit_text, inline=True)

        if self.participants:
            lista = "\n".join([f"{i+1}. {m.mention}" for i, m in enumerate(self.participants)])
        else:
            lista = "Még nincs jelentkező."

        embed.add_field(name="Jelentkezők", value=lista, inline=False)
        embed.set_footer(text="Válassz új eseményt a menüből, vagy használd a gombokat!")
        return embed

    @discord.ui.button(label="Jelentkezés", style=discord.ButtonStyle.success, custom_id="join_btn")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in self.participants:
            await interaction.response.send_message("Már jelentkeztél erre az eseményre!", ephemeral=True)
            return

        limit = self.config["limit"]
        if limit is not None and len(self.participants) >= limit:
            await interaction.response.send_message("Sajnos ez az esemény már betelt!", ephemeral=True)
            return

        self.participants.append(interaction.user)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Leiratkozás", style=discord.ButtonStyle.secondary, custom_id="leave_btn")
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.participants:
            await interaction.response.send_message("Nem vagy rajta a jelentkezési listán!", ephemeral=True)
            return

        self.participants.remove(interaction.user)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Esemény törlése", style=discord.ButtonStyle.danger, custom_id="delete_btn")
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_creator = interaction.user.id == self.creator.id
        is_admin = interaction.user.guild_permissions.administrator

        if not (is_creator or is_admin):
            await interaction.response.send_message("Csak a szervező vagy egy adminisztrátor törölheti az eseményt!", ephemeral=True)
            return

        await interaction.message.delete()
        await interaction.response.send_message(f"Az eseményt törölte: {interaction.user.mention}", ephemeral=True)

class EventSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Mino run", description="Run (Max 4 fő)", emoji="🐂"),
            discord.SelectOption(label="Féreg run", description="Run (Max 4 fő)", emoji="🐛"),
            discord.SelectOption(label="Kenta run", description="Run (Max 4 fő)", emoji="🏹"),
            discord.SelectOption(label="Menedék expo", description="Expedíció (Max 5 fő)", emoji="🏕️"),
            discord.SelectOption(label="Ork Expo", description="Expedíció (Max 5 fő)", emoji="👹"),
            discord.SelectOption(label="Sivatag Expo", description="Expedíció (Max 5 fő)", emoji="🏜️"),
            discord.SelectOption(label="Klán Zállítás", description="Klán Zászló (Nincs limit)", emoji="🚩"),
        ]
        super().__init__(placeholder="Válassz eseményt...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_event = self.values[0]
        new_view = EventView(creator=interaction.user, event_name=selected_event)
        await interaction.response.edit_message(embed=new_view.build_embed(), view=new_view)

@bot.tree.command(name="esemeny", description="Esemény panel megnyitása")
async def esemeny(interaction: discord.Interaction):
    default_event = "Mino run"
    view = EventView(creator=interaction.user, event_name=default_event)
    await interaction.response.send_message(embed=view.build_embed(), view=view)

@bot.event
async def on_ready():
    print(f"Bejelentkezve mint: {bot.user.name}")
    try:
        await bot.tree.sync()
        print("Parancsok szinkronizálva!")
    except Exception as e:
        print(f"Szinkronizációs hiba: {e}")

if not TOKEN:
    print("HIBA: A DISCORD_TOKEN környezeti változó nincs beállítva!")
else:
    bot.run(TOKEN)
