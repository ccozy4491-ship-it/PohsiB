import discord
from discord import app_commands
from discord.ext import commands

# --- BEÁLLÍTÁSOK ---
TOKEN = MTU1NjU2Mjc3MDQxNjExNTgwMw.GB6M6G.IKC-x5QHFCXc_ZpBgGpD_Ie76Rx5gn2C961LDk
GUILD_ID = 1539231576242659418  # cseréld ki a szervered ID-jára!

# Esemény típusok beállításai és létszámstátuszai (None = nincs korlát)
EVENT_CONFIG = {
    # Runok (Max 4 fő)
    "Mino run": {"type": "Run", "limit": 4},
    "Féreg run": {"type": "Run", "limit": 4},
    "Kenta run": {"type": "Run", "limit": 4},
    # Expedíciók (Max 5 fő)
    "Menedék expo": {"type": "Expedíció", "limit": 5},
    "Ork Expo": {"type": "Expedíció", "limit": 5},
    "Sivatag Expo": {"type": "Expedíció", "limit": 5},
    # Klán Zászló (Korlátlan)
    "Klán Zászló": {"type": "Klán Zászló", "limit": None}
}

class EventBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Parancsok szinkronizálása csak a megadott szerverre
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print(f"Parancsok szinkronizálva a(z) {GUILD_ID} szerverre!")

bot = EventBot()

# --- NÉZET ÉS INTERAKTÍV ELEMEK ---
class EventView(discord.ui.View):
    def __init__(self, creator: discord.Member, event_name: str):
        super().__init__(timeout=None)
        self.creator = creator
        self.event_name = event_name
        self.participants = [creator]  # A létrehozó automatikusan feliratkozik
        self.config = EVENT_CONFIG[event_name]

        # Választómenü hozzáadása
        self.add_item(EventSelect())

    def build_embed(self) -> discord.Embed:
        limit_text = "Nincs korlát" if self.config["limit"] is None else f"{len(self.participants)}/{self.config['limit']}"
        
        embed = discord.Embed(
            title=f"⚔️ Esemény: {self.event_name}",
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
            # Runok
            discord.SelectOption(label="Mino run", description="Run (Max 4 fő)", emoji="🐂"),
            discord.SelectOption(label="Féreg run", description="Run (Max 4 fő)", emoji="🐛"),
            discord.SelectOption(label="Kenta run", description="Run (Max 4 fő)", emoji="🏹"),
            # Expedíciók
            discord.SelectOption(label="Menedék expo", description="Expedíció (Max 5 fő)", emoji="🏕️"),
            discord.SelectOption(label="Ork Expo", description="Expedíció (Max 5 fő)", emoji="👹"),
            discord.SelectOption(label="Sivatag Expo", description="Expedíció (Max 5 fő)", emoji="🏜️"),
            # Klán Zászló
            discord.SelectOption(label="Klán Zászló", description="Klán Zászló (Nincs limit)", emoji="🚩"),
        ]
        super().__init__(placeholder="Válassz eseményt...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_event = self.values[0]
        # Új nézet létrehozása a kiválasztott eseménnyel
        new_view = EventView(creator=interaction.user, event_name=selected_event)
        await interaction.response.edit_message(embed=new_view.build_embed(), view=new_view)


# --- PARANCSOK ---
@bot.tree.command(name="esemeny", description="Esemény panel megnyitása")
async def esemeny(interaction: discord.Interaction):
    # Alapértelmezett kezdő esemény: Mino run
    default_event = "Mino run"
    view = EventView(creator=interaction.user, event_name=default_event)
    await interaction.response.send_message(embed=view.build_embed(), view=view)


@bot.event
async def on_ready():
    print(f"Bejelentkezve mint: {bot.user.name}")

bot.run(TOKEN)
