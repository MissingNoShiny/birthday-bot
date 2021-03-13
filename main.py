import asyncio
import sqlite3

from configparser import ConfigParser
from datetime import datetime

from discord.ext import commands, tasks


class DateConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        for date_format in ('%d/%m/%Y', '%d/%m'):
            try:
                return datetime.strptime(argument, date_format)
            except ValueError:
                pass
        raise commands.BadArgument()


config = ConfigParser()
config.read('config.ini')
token = config['discord']['token']
channel_id = int(config['discord']['channel_id'])

db = sqlite3.connect('birthdays.db')
db.execute("""CREATE TABLE IF NOT EXISTS birthdays (
                            user_id integer PRIMARY KEY,
                            day integer NOT NULL,
                            month integer NOT NULL,
                            year integer
                    );""")
db.commit()

bot = commands.Bot(command_prefix='$')


@bot.command(aliases=['anniversaire'])
async def birthday(ctx: commands.Context, date: DateConverter):
    if date > datetime.now():
        await ctx.send('Cette date est dans le futur !')
        return

    year = date.year if date.year > 1900 else None
    db.execute("""INSERT INTO birthdays (user_id, day, month, year) VALUES (?, ?, ?, ?)
                  ON CONFLICT(user_id) DO UPDATE SET day = ?, month = ?, year = ?;""",
               (ctx.author.id, date.day, date.month, year, date.day, date.month, year))
    db.commit()
    await ctx.send('Date mise à jour')


@birthday.error
async def birthday_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.BadArgument):
        return await ctx.send('Date invalide')


@tasks.loop(hours=24)
async def happy_birthday():
    now = datetime.now()
    cursor = db.execute("""SELECT user_id, year from birthdays WHERE month = ? AND day = ?;""", (now.month, now.day))
    channel = await bot.fetch_channel(channel_id)
    for row in cursor:
        age_string = f" ({now.year - row[1]} ans)" if row[1] else ""
        await channel.send(
            f"Aujourd'hui, c'est l'anniversaire de {(await bot.fetch_user(row[0])).mention}{age_string} !")
    cursor.close()


@happy_birthday.before_loop
async def happy_birthday_before():
    now = datetime.now()
    delta = datetime.now().replace(day=now.day + 1, hour=0, minute=0, second=0) - now
    await asyncio.sleep(delta.total_seconds())


@bot.command()
async def test(ctx):
    await happy_birthday()


@bot.event
async def on_ready():
    happy_birthday.start()
    print('Ready')


bot.run(token)
