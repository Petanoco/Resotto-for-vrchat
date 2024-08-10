import logging
import io
import os
import sys
from datetime import datetime
from typing import Union
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image
from fileloader import Config, ChannelsLoader, WhitelistableGuildsLoader
from typing import Union

# ルートディレクトリを取得
if hasattr(sys, '_MEIPASS'):
    root_path = os.path.dirname(sys.executable)
else:
    root_path = os.path.dirname(os.path.abspath(__file__))

DIRECTORY_LOG = os.path.join(root_path, "log")
DIRECTORY_CONFIG = os.path.join(root_path, "config")
FILE_LOG_TIMESTAMPED=f'fdiscord_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
FILE_LOG='fdiscord.log'

CONFIG: Config = Config.load()


filename = FILE_LOG_TIMESTAMPED if CONFIG.use_timestamped_logfilename else FILE_LOG
logging.basicConfig(
    handlers=[
        logging.FileHandler(os.path.join(DIRECTORY_LOG, filename), encoding='utf-8', mode='w'),
        logging.StreamHandler()],
    format='%(asctime)s | %(name)-15s | %(levelname)-8s | %(message)s',
    level=CONFIG.log_level_value
)


class Resotto(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        intents.dm_messages = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.tree.add_command(add_channel)
        self.tree.add_command(remove_channel)
        self.tree.add_command(get_channels)
        self.tree.add_command(enable_channel_whitelist)
        self.tree.add_command(disable_channel_whitelist)
        logging.info("resync server commands")
        await self.tree.sync()
bot = Resotto()


WHITELISTED_CHANNEL_IDS = ChannelsLoader.loadChannels()
WHITELISTED_GUILD_IDS = WhitelistableGuildsLoader.loadGuilds()

def getChannelName(channel: Union[discord.TextChannel, discord.StageChannel, discord.VoiceChannel, discord.Thread, discord.DMChannel, discord.GroupChannel, discord.PartialMessageable]) -> str:
    if isinstance(channel, discord.TextChannel) or isinstance(channel, discord.Thread):
        return f"{channel.name}@{channel.guild.name}"
    elif isinstance(channel, discord.DMChannel):
        return "DirectMessage"
    elif isinstance(channel, discord.GroupChannel):
        return "GroupMessage"
    else:
        return "UnknownChannel"

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name=CONFIG.presence))
    logging.info(f'Bot is ready! Logged in as {bot.user}')

@bot.event
async def on_message(message: discord.Message):
    if (message.author.bot):
        return
    logging.debug("on_message fired")
    is_whitelisted = (message.guild) and (message.guild.id in WHITELISTED_GUILD_IDS)
    if (is_whitelisted) and (message.channel.id not in WHITELISTED_CHANNEL_IDS):
        logging.debug("    message is sent in unlisted channel, skipped")
        return
    image_filess = [attachment for attachment in message.attachments if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
    if (len(image_filess) == 0):
        logging.debug("    message has no attachments, skipped")
        return
    logging.debug("    passed")
    
    logging.info(f"Received message from {message.author.name}({message.author.id}) in {getChannelName(message.channel)}({message.channel.id}) with {len(message.attachments)} files")
    async with message.channel.typing():
        output_files = []
        for attachment in image_filess:
            if (CONFIG.max_file_count>0) and (len(output_files) >= CONFIG.max_file_count):
                break
            # 画像ファイルを展開
            image = Image.open(io.BytesIO(await attachment.read()))
            # 画像の縦横ピクセル数の大きい方が2048になるように等率で縮小
            longerEdgeLength = max(image.width, image.height)
            if (longerEdgeLength > CONFIG.target_resolution):
                scale = min(CONFIG.target_resolution / image.width, CONFIG.target_resolution / image.height)
                new_size = (int(image.width * scale), int(image.height * scale))
                resized_image = image.resize(new_size, CONFIG.resampling_value)
                # 画像をバイナリデータに変換
                byte_arr = io.BytesIO()
                resized_image.save(byte_arr, format=image.format)
                byte_arr.seek(0)
                output_files.append(discord.File(fp=byte_arr, filename=f"resized_{attachment.filename}"))
        
        low_reso_files_count = len(image_filess) - len(output_files)
        if low_reso_files_count > 0 :
            await message.reply(files = output_files, content=f"{low_reso_files_count} 個の画像は解像度が十分低いため縮小されませんでした")
        else:
            await message.reply(files = output_files)


@app_commands.guild_only()
@app_commands.default_permissions(manage_channels=True)
@app_commands.command(name ="add_resize_channel",description="チャンネルを画像処理のチェック対象に加えます(ホワイトリスト式の場合)")
async def add_channel(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if (interaction.channel_id not in WHITELISTED_CHANNEL_IDS):
        logging.info(f"Add channel to the whitelist: {interaction.channel.name}@{interaction.channel.guild}({interaction.channel_id})")
        WHITELISTED_CHANNEL_IDS.append(interaction.channel_id)
    await interaction.followup.send(f"channel: #{interaction.channel.name} added!")
    ChannelsLoader.saveChannels(WHITELISTED_CHANNEL_IDS)

@app_commands.guild_only()
@app_commands.default_permissions(manage_channels=True)
@app_commands.command(name ="remove_resize_channel",description="チャンネルを画像処理のチェック対象から外します(チャンネルホワイトリスト有効の場合)")
async def remove_channel(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if (interaction.channel_id in WHITELISTED_CHANNEL_IDS):
        logging.info(f"Remove channel from the whitelist: {interaction.channel.name}@{interaction.channel.guild}({interaction.channel_id})")
        WHITELISTED_CHANNEL_IDS.remove(interaction.channel_id)
    await interaction.followup.send(f"channel: #{interaction.channel.name} added!")
    ChannelsLoader.saveChannels(WHITELISTED_CHANNEL_IDS)

@app_commands.guild_only()
@app_commands.command(name ="get_resize_channels",description="画像処理を行えるチャンネル一覧を表示します(チャンネルホワイトリスト有効の場合)")
async def get_channels(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    def get_is_guild(channel_id: int):
        channel = bot.get_channel(channel_id)
        return (channel) and (isinstance(channel, discord.TextChannel) or isinstance(channel, discord.Thread))
    channels = [bot.get_channel(channel_id) for channel_id in WHITELISTED_CHANNEL_IDS if get_is_guild(channel_id)]
    my_channels = [channel for channel in channels if (channel) and (channel.guild==interaction.guild)]
    message = "\n".join([f"[{c.name}](https://discord.com/channels/{c.guild.id}/{c.id})" for c in my_channels])
    await interaction.followup.send(message)


@app_commands.guild_only()
@app_commands.default_permissions(manage_guild=True)
@app_commands.command(name ="enable_channel_whitelist",description="特定のチャンネルでのみ画像処理を行うよう設定します")
async def enable_channel_whitelist(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if (interaction.guild_id not in WHITELISTED_GUILD_IDS):
        logging.info(f"Whitelist is enabled: {interaction.guild.name}({interaction.guild_id})")
        WHITELISTED_GUILD_IDS.append(interaction.guild_id)
    await interaction.followup.send(f"Channel whitelist is enabled!")
    logging.error(interaction.guild_id)
    logging.warning(interaction.channel_id)
    for id in WHITELISTED_GUILD_IDS:
        logging.error(id)
    WhitelistableGuildsLoader.saveGuilds(WHITELISTED_GUILD_IDS)

@app_commands.guild_only()
@app_commands.default_permissions(manage_guild=True)
@app_commands.command(name ="disable_channel_whitelist",description="特定のチャンネルでのみ画像処理を行う設定を解除します")
async def disable_channel_whitelist(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if (interaction.guild_id in WHITELISTED_GUILD_IDS):
        logging.info(f"Whitelist is disabled: {interaction.guild.name}({interaction.guild_id})")
        WHITELISTED_GUILD_IDS.remove(interaction.guild_id)
    await interaction.followup.send(f"Channel whitelist is disabled!")
    WhitelistableGuildsLoader.saveGuilds(WHITELISTED_GUILD_IDS)


def main():
    logging.getLogger('discord')
    maskedToken = '*' * len(CONFIG.token)
    logging.info(f"Starting GoldenBot with token: {maskedToken}")
    try:
        bot.run(CONFIG.token, log_level=CONFIG.log_level_value, log_handler=None)
    except discord.errors.LoginFailure:
        logging.fatal("認証に失敗しました")
        raise
    except discord.errors.PrivilegedIntentsRequired:
        logging.fatal("必要な権限がありません, Botページから MessageContentIntent を有効化してください -> https://discord.com/developers/applications/")
        raise

if __name__ == "__main__":
    main()
