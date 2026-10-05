import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands

# --- DISCORD BOT BEÁLLÍTÁSOK ---
TOKEN = os.environ.get("DISCORD_TOKEN")
GUILD_ID = 1539231576242659418  # A megadott Discord szerver azonosítója

EVENT_TYPES = {
    "Mino run": {"type": "Run", "limit": 4},
    "Féreg run": {"type": "Run", "limit": 4},
    "Kenta run": {"type": "Run", "limit": 4},
    "Menedék expo": {"type": "Expedíció", "limit": 5},
    "Ork Expo": {"type": "Expedíció", "limit": 5},
    "Sivatag Expo": {"type": "Expedíció", "limit": 5},
    "Klán Zászló": {"type": "Klán Zászló", "limit": None}
}

# Alapértelmezett intents - NO message_content a rate limit megelőzésére!
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- PUBLIC ESEMÉNY PANEL ---
class PublicEventView(discord.ui.View):
    def __init__(self, creator: discord.Member, title: str, event_type: str, date_time: str):
        super().__init__(timeout=None)
        self.creator = creator
        self.title = title
        self.event_type = event_type
        self.date_time = date_time
        self.participants = [creator]
        self.config = EVENT_TYPES[event_type]

    def build_embed(self) -> discord.Embed:
        limit_text = "Nincs korlát" if self.config["limit"] is None else f"{len(self.participants)}/{self.config['limit']}"
        
        embed = discord.Embed(
            title=f"⚔ {self.title}",
            description=f"**Típus:** {self.event_type} ({self.config['type']})",
            color=discord.Color.blue()
        )
        embed.add_field(name="Szervező", value=self.creator.mention, inline=True)
        embed.add_field(name="Időpont", value=f"⏰ {self.date_time}", inline=True)
        embed.add_field(name="Létszám", value=limit_text, inline=True)

        if self.participants:
            lista = "\n".join([f"{i+1}. {m.mention}" for i, m in enumerate(self.participants)])
        else:
            lista = "Még nincs jelentkező."

        embed.add_field(name="Jelentkezők", value=lista, inline=False)
        embed.set_footer(text="A gombok segítségével csatlakozhatsz vagy leiratkozhatsz.")
        return embed

    @discord.ui.button(label="Jelentkezés", style=discord.ButtonStyle.success, custom_id="join_btn")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in self.participants:
            await interaction.response.send_message("Már jelentkeztél erre az eseményre!", ephemeral=True)
            return

        limit = self.config["limit"]
        if limit is not None and len(self.participants) >= limit:
            await interaction.response.send_message("Sajnos ez an esemény már betelt!", ephemeral=True)
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

# --- PRIVÁT BEÁLLÍTÓ PANEL ---
class SetupModal(discord.ui.Modal, title="Esemény részletei"):
    event_title = discord.ui.TextInput(
        label="Esemény címe",
        placeholder="pl. Esti Klán Run",
        max_length=100,
        required=True
    )
    event_time = discord.ui.TextInput(
        label="Időpont",
        placeholder="pl. Ma 20:00 vagy 2026.10.05 20:00",
        max_length=50,
        required=True
    )

    def __init__(self, selected_type: str):
        super().__init__()
        self.selected_type = selected_type

    async def on_submit(self, interaction: discord.Interaction):
        public_view = PublicEventView(
            creator=interaction.user,
            title=self.event_title.value,
            event_type=self.selected_type,
            date_time=self.event_time.value
        )
        await interaction.channel.send(embed=public_view.build_embed(), view=public_view)
        await interaction.response.send_message("✅ Esemény sikeresen létrehozva és közzétéve!", ephemeral=True)

class EventTypeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Mino run", description="Run (Max 4 fő)", emoji="🐂"),
            discord.SelectOption(label="Féreg run", description="Run (Max 4 fő)", emoji="🐛"),
            discord.SelectOption(label="Kenta run", description="Run (Max 4 fő)", emoji="🏹"),
            discord.SelectOption(label="Menedék expo", description="Expedíció (Max 5 fő)", emoji="🏕️"),
            discord.SelectOption(label="Ork Expo", description="Expedíció (Max 5 fő)", emoji="👹"),
            discord.SelectOption(label="Sivatag Expo", description="Expedíció (Max 5 fő)", emoji="🏜️"),
            discord.SelectOption(label="Klán Zászló", description="Klán Zászló (Nincs limit)", emoji="🚩"),
        ]
        super().__init__(placeholder="Válassz esemény típust...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        modal = SetupModal(selected_type=self.values[0])
        await interaction.response.send_modal(modal)

class PrivateSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(EventTypeSelect())

@bot.tree.command(name="esemeny", description="Új esemény panel létrehozása")
async def esemeny(interaction: discord.Interaction):
    view = PrivateSetupView()
    await interaction.response.send_message("🛠️ **Esemény Létrehozása**\nVálaszd ki az esemény típusát a folytatáshoz:", view=view, ephemeral=True)

# --- BEJELENTKEZÉS ÉS PARANCS SZINKRON ---
@bot.event
async def on_ready():
    print(f"✅ Bot csatlakozva: {bot.user.name}")
    try:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"✅ {len(synced)} Slash parancs szinkronizálva ({GUILD_ID})!")
    except Exception as e:
        print(f"⚠️ Szinkronizációs figyelmeztetés: {e}")

# --- ROBUSZTUS INDÍTÓ FÜGGVÉNY RATE LIMIT ELLEN ---
async def start_bot():
    retry_delay = 15  # Másodperc várakozás 429-es hiba esetén
    while True:
        try:
            await bot.start(TOKEN)
            break
        except discord.errors.HTTPException as e:
            if e.status == 429:
                print(f"⚠️ 429 Too Many Requests (Rate limit). Várakozás {retry_delay} másodpercig az újracsatlakozás előtt...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 120)  # Növeljük a várakozási időt
            else:
                raise e

if __name__ == "__main__":
    if not TOKEN:
        print("HIBA: A DISCORD_TOKEN környezeti változó hiányzik!")
    else:
        try:
            asyncio.run(start_bot())
        except KeyboardInterrupt:
            print("Bot leállítva.")
