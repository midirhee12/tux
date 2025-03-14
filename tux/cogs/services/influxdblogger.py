import influxdb_client
from discord.ext import commands, tasks
from influxdb_client import Point
from influxdb_client.client.write_api import SYNCHRONOUS
from loguru import logger

from tux.bot import Tux
from tux.database.client import db
from tux.utils.config import CONFIG


class InfluxLogger(commands.Cog):
    def __init__(self, bot):
        self.bot = Tux
        if self.init_influx():
            logger.info("starting influxdb logger")
            self.logger.start()
        else:
            logger.error("influxdb logger failed to init.")

    def cog_unload(self):
        self.logger.cancel()

    def init_influx(self):
        influx_token = CONFIG.INFLUXDB_TOKEN
        influx_url = CONFIG.INFLUXDB_URL
        self.influx_org = CONFIG.INFLUXDB_ORG
        if (influx_token != "") and (influx_url != "") and (self.influx_org != ""):
            write_client = influxdb_client.InfluxDBClient(url=influx_url, token=influx_token, org=self.influx_org)
            self.influx_write_api = write_client.write_api(write_options=SYNCHRONOUS)
            return True
        return False

    @tasks.loop(seconds=60)
    async def logger(self):
        influx_bucket = "tux stats"
        # Collect the guild list from the database, we'll need this to sort everything by.
        guild_list = await db.guild.find_many()

        # TODO: Add more detailed stats on cases, add stats on reminders and level system
        # iterate down the guildlist and run logging for each entry
        for i in guild_list:
            # Collect data by querying the db and filtering results to only include the guild we're currently working on
            starboard_stats = await db.starboardmessage.find_many(
                where={
                    "message_guild_id": i.guild_id,
                },
            )
            snippet_stats = await db.snippet.find_many(
                where={
                    "guild_id": i.guild_id,
                },
            )
            afk_stats = await db.afkmodel.find_many(
                where={
                    "guild_id": i.guild_id,
                },
            )
            case_stats = await db.case.find_many(
                where={
                    "guild_id": i.guild_id,
                },
            )
            points = [
                Point("guild stats").tag("guild", i.guild_id).field("starboard count", len(starboard_stats)),
                Point("guild stats").tag("guild", i.guild_id).field("snippet count", len(snippet_stats)),
                Point("guild stats").tag("guild", i.guild_id).field("afk count", len(afk_stats)),
                Point("guild stats").tag("guild", i.guild_id).field("case count", len(case_stats)),
            ]
            self.influx_write_api.write(bucket=influx_bucket, org="docs", record=points)


async def setup(bot: Tux) -> None:
    await bot.add_cog(InfluxLogger(bot))
