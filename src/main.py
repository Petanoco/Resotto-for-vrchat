import logging
import io
import os
import sys
import json
import discord
from discord.ext import commands
from PIL import Image
from config import Config

if hasattr(sys, '_MEIPASS'):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

DIRECTORY_LOG = os.path.join(base_path, "log")
DIRECTORY_CONFIG = os.path.join(base_path, "config")
#FILE_LOG=f'fdiscord_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
FILE_LOG='fdiscord.log'
FILE_TARGET_CHANNELS = "target_channels.json"
FILE_CONFIG = "config.json"
CONFIG: Config = Config.load(os.path.join(DIRECTORY_CONFIG, FILE_CONFIG))

logging.basicConfig(
    handlers=[
        logging.FileHandler(os.path.join(DIRECTORY_LOG, FILE_LOG), encoding='utf-8', mode='w'),
        logging.StreamHandler()],
    format='%(asctime)s | %(name)-15s | %(levelname)-8s | %(message)s',
    level=CONFIG.log_level_value
)

def generate_bot() -> commands.bot:
    intents = discord.Intents.default()
    intents.messages = True
    intents.message_content = True
    intents.dm_messages = True
    return commands.Bot(command_prefix="!", intents=intents)
bot = generate_bot()

def saveChannels():
    try:
        with open(os.path.join(DIRECTORY_CONFIG, FILE_TARGET_CHANNELS), "w", encoding="utf-8") as file:
            json.dump(TARGET_CHANNELS, file, ensure_ascii=False, indent=4)
    except PermissionError:
        logging.error("権限エラー: 設定ファイルを保存できません")
def loadChannels() -> list[int]:
    path = os.path.join(DIRECTORY_CONFIG, FILE_TARGET_CHANNELS)
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    else:
        return []
TARGET_CHANNELS: list[int] = loadChannels()

@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user}')
    await bot.change_presence(activity=discord.Game(name=CONFIG.presence))
    await bot.tree.sync()
@bot.event
async def on_message(message: discord.Message):
    logging.debug("on_message fired")
    if (message.author.bot):
        logging.debug("    message author is a bot, skipped")
        return
    if (CONFIG.is_whitelisted) and (message.channel.id not in TARGET_CHANNELS):
        logging.debug("    message is sent in unlisted channel, skipped")
        return
    if (len(message.attachments) == 0):
        logging.debug("    message has no attachments, skipped")
        return
    if (message.author.name in CONFIG.ignore_user_ids):
        logging.debug("    message author is ignore listed, skipped")
        return
    logging.debug("    passed")
    logging.info(f"Received message from {message.author.name}({message.author.id}) in {message.channel.name}@{message.channel.guild.name}({message.channel.id}) with {len(message.attachments)} files")
    async with message.channel.typing():
        files = []
        for attachment in message.attachments:
            if (CONFIG.max_file_count>0) and (len(files) >= CONFIG.max_file_count):
                break
            if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                # 画像ファイルをダウンロード
                img_data = await attachment.read()
                image = Image.open(io.BytesIO(img_data))
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
                    files.append(discord.File(fp=byte_arr, filename=f"resized_{attachment.filename}"))
        if len(files) > 0:
            await message.reply(files = files)

@bot.tree.command(name ="add_resize_channel",description="チャンネルを画像処理のチェック対象に加えます(ホワイトリスト式の場合)")
async def add_channel(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    if (interaction.channel_id not in TARGET_CHANNELS):
        logging.info(f"Add channel to the whitelist: {interaction.channel.name}@{interaction.channel.guild}({interaction.channel_id})")
        TARGET_CHANNELS.append(interaction.channel_id)
    await interaction.followup.send(f"channel: #{interaction.channel.name} added!")
    saveChannels()
@bot.tree.command(name ="remove_resize_channel",description="チャンネルを画像処理のチェック対象から外します(ホワイトリスト式の場合)")
async def remove_channel(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    if (interaction.channel_id in TARGET_CHANNELS):
        logging.info(f"Remove channel from the whitelist: {interaction.channel.name}@{interaction.channel.guild}({interaction.channel_id})")
        TARGET_CHANNELS.remove(interaction.channel_id)
    await interaction.followup.send(f"channel: #{interaction.channel.name} added!")
    saveChannels()

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
