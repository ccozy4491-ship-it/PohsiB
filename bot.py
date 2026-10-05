import asyncio
import os
import discord
from discord import app_commands
from discord.ext import commands
import database as db

TOKEN = os.environ.get("DISCORD_TOKEN")
GUILD_ID = int(os.environ.get("GUILD_ID", 1539231576242659418))

EVENT_TYPES = {
    "Mino run": {"type": "Run", "limit": 4},
    "Féreg run": {"type": "Run", "limit": 4},
    "Kenta run": {"type": "Run", "limit": 4},
    "Menedék expo": {"type": "Expedíció", "limit": 5},
    "Ork Expo": {"type": "Expedíció", "limit": 5},
    "Sivatag Expo": {"type": "Expedíció", "limit": 5},
    "Klán Zászló": {"type": "Klán Zászló", "limit": None},
}

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


def build_event_embed(
    title: str,
    event_type: str,
    creator_mention: str,
    date_time: str,
    participants: list[str],
) -> discord.Embed:
    config = EVENT_TYPES.get(event_type, {"type": "Esemény", "limit": None})
    limit = config["limit"]
    limit_text = (
        "Nincs korlát"
        if limit is None
        else f"{len(participants)}/{limit}"
    )

    embed = discord.Embed(
        title=f"⚔ {title}",
        description=f"**Típus:** {event_type} ({config['type']})",
        color=discord.Color.blue(),
    )
    embed.add_field(name="Szervező", value=creator_mention, inline=True)
    embed.add_field(name="Időpont", value=f"⏰ {date_time}", inline=True)
    embed.add_field(name="Létszám", value=limit_text, inline=True)

    if participants:
        lista = "\n".join(
            [f"{i+1}. <@{user_id}>" for i, user_id in enumerate(participants)]
        )
    else:
        lista = "Még nincs jelentkező."

    embed.add_field(name="Jelentkezők", value=lista, inline=False)
    embed.set_footer(
        text="A gombok segítségével csatlakozhatsz vagy leiratkozhatsz."
    )
    return embed


class PublicEventView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Jelentkezés",
        style=discord.ButtonStyle.success,
        custom_id="join_btn",
    )
    async def join_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        event = db.get_event_by_message_id(interaction.message.id)
        if not event:
            await interaction.response.send_message(
                "Ez az esemény már nem található az adatbázisban!", ephemeral=True
            )
            return

        participants = db.get_participants(event["id"])
        user_id_str = str(interaction.user.id)

        if user_id_str in participants:
            await interaction.response.send_message(
                "Már jelentkeztél erre az eseményre!", ephemeral=True
            )
            return

        limit = EVENT_TYPES.get(event["event_type"], {}).get("limit")
        if limit is not None and len(participants) >= limit:
            await interaction.response.send_message(
                "Sajnos ez az esemény már betelt!", ephemeral=True
            )
            return

        db.add_participant(event["id"], user_id_str)
        updated_participants = db.get_participants(event["id"])

        embed = build_event_embed(
            title=event["title"],
            event_type=event["event_type"],
            creator_mention=f"<@{event['creator_id']}>",
            date_time=event["date_time"],
            participants=updated_participants,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="Leiratkozás",
        style=discord.ButtonStyle.secondary,
        custom_id="leave_btn",
    )
    async def leave_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        event = db.get_event_by_message_id(interaction.message.id)
        if not event:
            await interaction.response.send_message(
                "Ez az esemény már nem található!", ephemeral=True
            )
            return

        participants = db.get_participants(event["id"])
        user_id_str = str(interaction.user.id)

        if user_id_str not in participants:
            await interaction.response.send_message(
                "Nem vagy rajta a jelentkezési listán!", ephemeral=True
            )
            return

        db.remove_participant(event["id"], user_id_str)
        updated_participants = db.get_participants(event["id"])

        embed = build_event_embed(
            title=event["title"],
            event_type=event["event_type"],
            creator_mention=f"<@{event['creator_id']}>",
            date_time=event["date_time"],
            participants=updated_participants,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="Esemény törlése",
        style=discord.ButtonStyle.danger,
        custom_id="delete_btn",
    )
    async def delete_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        event = db.get_event_by_message_id(interaction.message.id)
        if not event:
            await interaction.message.delete()
            return

        is_creator = str(interaction.user.id) == str(event["creator_id"])
        is_admin = interaction.user.guild_permissions.administrator

        if not (is_creator or is_admin):
            await interaction.response.send_message(
                "Csak a szervező vagy egy adminisztrátor törölheti az"
                " eseményt!",
                ephemeral=True,
            )
            return

        db.delete_event(event["id"])
        await interaction.message.delete()
        await interaction.response.send_message(
            f"Az eseményt törölte: {interaction.user.mention}", ephemeral=True
        )


class SetupModal(discord.ui.Modal, title="Esemény részletei"):
    event_title = discord.ui.TextInput(
        label="Esemény címe",
        placeholder="pl. Esti Klán Run",
        max_length=100,
        required=True,
    )
    event_time = discord.ui.TextInput(
        label="Időpont",
        placeholder="pl. Ma 20:00 vagy 2026.10.05 20:00",
        max_length=50,
        required=True,
    )

    def __init__(self, selected_type: str):
        super().__init__()
        self.selected_type = selected_type

    async def on_submit(self, interaction: discord.Interaction):
        creator_id = str(interaction.user.id)
        public_view = PublicEventView()

        embed = build_event_embed(
            title=self.event_title.value,
            event_type=self.selected_type,
            creator_mention=interaction.user.mention,
            date_time=self.event_time.value,
            participants=[creator_id],
        )

        msg = await interaction.channel.send(embed=embed, view=public_view)

        event_id = db.create_event(
            message_id=msg.id,
            channel_id=msg.channel.id,
            creator_id=creator_id,
            title=self.event_title.value,
            event_type=self.selected_type,
            date_time=self.event_time.value,
        )
        db.add_participant(event_id, creator_id)

        await interaction.response.send_message(
            "✅ Esemény sikeresen létrehozva és közzétéve!", ephemeral=True
        )


class EventTypeSelect(discord.ui.Select):

    def __init__(self):
        options = [
            discord.SelectOption(
                label="Mino run", description="Run (Max 4 fő)", emoji="🐂"
            ),
            discord.SelectOption(
                label="Féreg run", description="Run (Max 4 fő)", emoji="🐛"
            ),
            discord.SelectOption(
                label="Kenta run", description="Run (Max 4 fő)", emoji="🏹"
            ),
            discord.SelectOption(
                label="Menedék expo",
                description="Expedíció (Max 5 fő)",
                emoji="🏕️",
            ),
            discord.SelectOption(
                label="Ork Expo",
                description="Expedíció (Max 5 fő)",
                emoji="👹",
            ),
            discord.SelectOption(
                label="Sivatag Expo",
                description="Expedíció (Max 5 fő)",
                emoji="🏜️",
            ),
            discord.SelectOption(
                label="Klán Zászló",
                description="Klán Zászló (Nincs limit)",
                emoji="🚩",
            ),
        ]
        super().__init__(
            placeholder="Válassz esemény típust...",
            min_values=1,
            max_values=1,
            options=options,
        )

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
    await interaction.response.send_message(
        "🛠️ **Esemény Létrehozása**\nVálaszd ki az esemény típusát a"
        " folytatáshoz:",
        view=view,
        ephemeral=True,
    )


@bot.event
async def on_ready():
    db.init_db()
    bot.add_view(PublicEventView())
    print(f"✅ Bot csatlakozva: {bot.user.name}")
    try:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"✅ {len(synced)} Slash parancs szinkronizálva ({GUILD_ID})!")
    except Exception as e:
        print(f"⚠️ Szinkronizációs figyelmeztetés: {e}")


async def start_bot():
    retry_delay = 15
    while True:
        try:
            await bot.start(TOKEN)
            break
        except discord.errors.HTTPException as e:
            if e.status == 429:
                print(
                    f"⚠️ 429 Rate limit. Várakozás {retry_delay} másodpercig..."
                )
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 120)
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
