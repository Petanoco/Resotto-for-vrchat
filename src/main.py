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
from fileloader import *
from typing import Union
import math

# ルートディレクトリを取得
if hasattr(sys, '_MEIPASS'):
    root_path = os.path.dirname(sys.executable)
else:
    root_path = os.path.dirname(os.path.abspath(__file__))

DIRECTORY_LOG = os.path.join(root_path, "log")
DIRECTORY_CONFIG = os.path.join(root_path, "config")
FILE_LOG_TIMESTAMPED=f'fdiscord_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
FILE_LOG='discord.log'

CONFIG: Config = ConfigLoader.load()


filename = FILE_LOG_TIMESTAMPED if CONFIG.use_timestamped_logfilename else FILE_LOG
if not os.path.exists(DIRECTORY_LOG):
    os.mkdir(DIRECTORY_LOG)
logging.basicConfig(
    handlers=[
        logging.FileHandler(os.path.join(DIRECTORY_LOG, filename), encoding='utf-8', mode='w'),
        logging.StreamHandler()],
    format='%(asctime)s | %(name)-15s | %(levelname)-8s | %(message)s',
    level=CONFIG.log_level_value
)

discord.VoiceClient.warn_nacl= False

class Resotto(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        intents.dm_messages = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.tree.add_command(add_workchannel_imageloader)
        self.tree.add_command(remove_workchannel_imageloader)
        self.tree.add_command(get_workchannels_imageloader)
        self.tree.add_command(add_workchannel_gallerywide)
        self.tree.add_command(remove_workchannel_gallerywide)
        self.tree.add_command(get_workchannels_gallerywide)
        self.tree.add_command(add_workchannel_gallerysquare)
        self.tree.add_command(remove_workchannel_gallerysquare)
        self.tree.add_command(get_workchannels_gallerysquare)
        self.tree.add_command(add_workchannel_gallerywide2square)
        self.tree.add_command(remove_workchannel_gallerywide2square)
        self.tree.add_command(get_workchannels_gallerywide2square)
        self.tree.add_command(enable_channel_whitelist)
        self.tree.add_command(disable_channel_whitelist)
        logging.info("resync server commands")
        await self.tree.sync()
bot = Resotto()


WHITELISTED_CHANNELS = ChannelsLoader.loadChannels()
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
    image_files = [attachment for attachment in message.attachments if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
    if (len(image_files) == 0):
        logging.debug("    message has no attachments, skipped")
        return
    
    is_whitelisted = (message.guild) and (message.guild.id in WHITELISTED_GUILD_IDS)
    is_target_of_imageloader = (not is_whitelisted) or (message.channel.id in WHITELISTED_CHANNELS.imageloaderChannels)
    is_target_of_gallerywide = (not is_whitelisted) or (message.channel.id in WHITELISTED_CHANNELS.galleryWideChannels)
    is_target_of_gallerysquare = (not is_whitelisted) or (message.channel.id in WHITELISTED_CHANNELS.gallerySquareChannels)
    is_target_of_gallerywide2square = (not is_whitelisted) or (message.channel.id in WHITELISTED_CHANNELS.galleryWideToSquareChannels)
    is_target_any = is_target_of_imageloader or is_target_of_gallerywide or is_target_of_gallerysquare or is_target_of_gallerywide2square
    
    if (is_target_any):
        async with message.channel.typing():
            await message.add_reaction("⏺️")
            output_files = []
            for i in range(min(len(image_files), CONFIG.max_file_count)):
                attachment = image_files[i]
                # 画像ファイルを展開
                sourceImage = Image.open(io.BytesIO(await attachment.read()))
                
                # ImageLoader向けの処理:
                # 画像の縦横ピクセル数の大きい方が2048になるように等率で縮小する
                if (is_target_of_imageloader):
                    #logging.info(f"Received message from {message.author.name}({message.author.id}) in {getChannelName(message.channel)}({message.channel.id}) with {len(message.attachments)} files")
                    longerEdgeLength = max(sourceImage.width, sourceImage.height)
                    if (longerEdgeLength > CONFIG.target_resolution):
                        scale = min(CONFIG.target_resolution / sourceImage.width, CONFIG.target_resolution / sourceImage.height)
                        new_size = (int(sourceImage.width * scale), int(sourceImage.height * scale))
                        resized_image = sourceImage.resize(new_size, CONFIG.resampling_value)
                        # 画像をバイナリデータに変換
                        byte_arr = io.BytesIO()
                        resized_image.save(byte_arr, format=sourceImage.format)
                        byte_arr.seek(0)
                        output_files.append(discord.File(fp=byte_arr, filename=f"imageloader_{attachment.filename}"))
                        
                # ギャラリー写真向けの処理
                # 16:9になるように透明ピクセルを追加(max2048x1152)
                if (is_target_of_gallerywide):
                    image = arrange_aspect_wide(sourceImage)
                    # 縮小
                    width, height = image.size
                    resized_image = image
                    if (width > CONFIG.gallery_wide_resolution):
                        target_width = CONFIG.gallery_wide_resolution
                        target_height = target_width * 9 / 16
                        scale = min(target_width / width, target_height / height)
                        new_size = (int(width * scale), int(height * scale))
                        resized_image = image.resize(new_size, CONFIG.resampling_value)
                    # 画像をバイナリデータに変換
                    byte_arr = io.BytesIO()
                    resized_image.save(byte_arr, format="png")
                    byte_arr.seek(0)
                    output_files.append(discord.File(fp=byte_arr, filename=f"wide_{attachment.filename}.png"))
                        
                # ギャラリーステッカー等向けの処理
                # 1:1になるように透明ピクセルを追加(max1024x1024)
                if (is_target_of_gallerysquare):
                    image = arrange_aspect_square(sourceImage)
                    # 縮小
                    width, height = image.size
                    resized_image = image
                    if (width > CONFIG.gallery_square_resolution):
                        new_size = (CONFIG.gallery_square_resolution, CONFIG.gallery_square_resolution)
                        resized_image = image.resize(new_size, CONFIG.resampling_value)
                    # 画像をバイナリデータに変換
                    byte_arr = io.BytesIO()
                    resized_image.save(byte_arr, format="png")
                    byte_arr.seek(0)
                    output_files.append(discord.File(fp=byte_arr, filename=f"square_{attachment.filename}.png"))
                        
                # ギャラリーステッカー用写真向けの処理
                # 適切に透明ピクセルを追加(max2048)
                if (is_target_of_gallerywide2square):
                    image = arrange_aspect_photo2square(sourceImage)
                    # 縮小
                    width, height = image.size
                    resized_image = image
                    if (width > CONFIG.gallery_wide_resolution):
                        target_width = CONFIG.gallery_wide_resolution
                        target_height = target_width * 9 / 16
                        scale = min(target_width / width, target_height / height)
                        new_size = (int(width * scale), int(height * scale))
                        resized_image = image.resize(new_size, CONFIG.resampling_value)
                    # 画像をバイナリデータに変換
                    byte_arr = io.BytesIO()
                    resized_image.save(byte_arr, format="png")
                    byte_arr.seek(0)
                    output_files.append(discord.File(fp=byte_arr, filename=f"squarewide_{attachment.filename}.png"))
            
            if len(output_files) > 0:
                await message.reply(files = output_files)
            await message.remove_reaction("⏺️", bot.user)
            await message.add_reaction("☑")

def arrange_aspect_wide(sourceImage: Image):
    width, height = sourceImage.size
    if ((sourceImage.width * 9.0) != (sourceImage.height * 16.0)):
        if ((sourceImage.width * 9.0) > (sourceImage.height * 16.0)): # 横長
            height = math.floor(width * 9.0 / 16.0)
        elif((sourceImage.width * 9.0) < (sourceImage.height * 16.0)): # 縦長
            width = math.floor(height * 16.0 / 9.0)
        # 16:9のアスペクト比のキャンバスを作成（透明ピクセルで埋める）
        aspect_ratio = (width, height)
        image = Image.new("RGBA", aspect_ratio, (0, 0, 0, 0))
        # 中央に配置
        offset_x = (image.width - sourceImage.width) // 2
        offset_y = (image.height - sourceImage.height) // 2
        image.paste(sourceImage, (offset_x, offset_y))
    else:
        image = sourceImage
    return image

def arrange_aspect_square(sourceImage: Image):
    width, height = sourceImage.size
    if (sourceImage.width != sourceImage.height):
        if ((sourceImage.width) > (sourceImage.height)): # 横長
            height = width
        elif((sourceImage.width) < (sourceImage.height)): # 縦長
            width = height
        logging.debug(width)
        logging.debug(height)
        # 1:1のアスペクト比のキャンバスを作成（透明ピクセルで埋める）
        aspect_ratio = (width, height)
        image = Image.new("RGBA", aspect_ratio, (0, 0, 0, 0))
        # 中央に配置
        offset_x = (image.width - sourceImage.width) // 2
        offset_y = (image.height - sourceImage.height) // 2
        image.paste(sourceImage, (offset_x, offset_y))
        return image
def arrange_aspect_photo2square(sourceImage: Image):
    return arrange_aspect_wide(arrange_aspect_square(sourceImage))

# コマンド定義
## ImageLoader 指定チャンネル管理
@app_commands.guild_only()
@app_commands.default_permissions(manage_channels=True)
@app_commands.command(name ="add_workchannel_imageloader",description="チャンネルを画像処理のチェック対象に加えます(ホワイトリスト式の場合)")
async def add_workchannel_imageloader(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if (interaction.channel_id not in WHITELISTED_CHANNELS.imageloaderChannels):
        logging.info(f"Add channel to the whitelist: {interaction.channel.name}@{interaction.channel.guild}({interaction.channel_id})")
        WHITELISTED_CHANNELS.imageloaderChannels.append(interaction.channel_id)
    await interaction.followup.send(f"channel: #{interaction.channel.name} added!")
    ChannelsLoader.saveChannels(WHITELISTED_CHANNELS)

@app_commands.guild_only()
@app_commands.default_permissions(manage_channels=True)
@app_commands.command(name ="remove_workchannel_imageloader",description="チャンネルを画像処理のチェック対象から外します(チャンネルホワイトリスト有効の場合)")
async def remove_workchannel_imageloader(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if (interaction.channel_id in WHITELISTED_CHANNELS.imageloaderChannels):
        logging.info(f"Remove channel from the whitelist: {interaction.channel.name}@{interaction.channel.guild}({interaction.channel_id})")
        WHITELISTED_CHANNELS.imageloaderChannels.remove(interaction.channel_id)
    await interaction.followup.send(f"channel: #{interaction.channel.name} added!")
    ChannelsLoader.saveChannels(WHITELISTED_CHANNELS)

@app_commands.guild_only()
@app_commands.command(name ="get_workchannels_imageloader",description="画像処理を行えるチャンネル一覧を表示します(チャンネルホワイトリスト有効の場合)")
async def get_workchannels_imageloader(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    def get_is_guild(channel_id: int):
        channel = bot.get_channel(channel_id)
        return (channel) and (isinstance(channel, discord.TextChannel) or isinstance(channel, discord.Thread))
    channels = [bot.get_channel(channel_id) for channel_id in WHITELISTED_CHANNELS.imageloaderChannels if get_is_guild(channel_id)]
    my_channels = [channel for channel in channels if (channel) and (channel.guild==interaction.guild)]
    message = "\n".join([f"[{c.name}](https://discord.com/channels/{c.guild.id}/{c.id})" for c in my_channels])
    await interaction.followup.send(message)
    
## ギャラリー写真向け 指定チャンネル管理
@app_commands.guild_only()
@app_commands.default_permissions(manage_channels=True)
@app_commands.command(name ="add_workchannel_gallerywide",description="チャンネルを画像処理のチェック対象に加えます(ホワイトリスト式の場合)")
async def add_workchannel_gallerywide(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if (interaction.channel_id not in WHITELISTED_CHANNELS.galleryWideChannels):
        logging.info(f"Add channel to the whitelist: {interaction.channel.name}@{interaction.channel.guild}({interaction.channel_id})")
        WHITELISTED_CHANNELS.galleryWideChannels.append(interaction.channel_id)
    await interaction.followup.send(f"channel: #{interaction.channel.name} added!")
    ChannelsLoader.saveChannels(WHITELISTED_CHANNELS)

@app_commands.guild_only()
@app_commands.default_permissions(manage_channels=True)
@app_commands.command(name ="remove_workchannel_gallerywide",description="チャンネルを画像処理のチェック対象から外します(チャンネルホワイトリスト有効の場合)")
async def remove_workchannel_gallerywide(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if (interaction.channel_id in WHITELISTED_CHANNELS.galleryWideChannels):
        logging.info(f"Remove channel from the whitelist: {interaction.channel.name}@{interaction.channel.guild}({interaction.channel_id})")
        WHITELISTED_CHANNELS.galleryWideChannels.remove(interaction.channel_id)
    await interaction.followup.send(f"channel: #{interaction.channel.name} added!")
    ChannelsLoader.saveChannels(WHITELISTED_CHANNELS)

@app_commands.guild_only()
@app_commands.command(name ="get_workchannels_gallerywide",description="画像処理を行えるチャンネル一覧を表示します(チャンネルホワイトリスト有効の場合)")
async def get_workchannels_gallerywide(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    def get_is_guild(channel_id: int):
        channel = bot.get_channel(channel_id)
        return (channel) and (isinstance(channel, discord.TextChannel) or isinstance(channel, discord.Thread))
    channels = [bot.get_channel(channel_id) for channel_id in WHITELISTED_CHANNELS.galleryWideChannels if get_is_guild(channel_id)]
    my_channels = [channel for channel in channels if (channel) and (channel.guild==interaction.guild)]
    message = "\n".join([f"[{c.name}](https://discord.com/channels/{c.guild.id}/{c.id})" for c in my_channels])
    await interaction.followup.send(message)
    
## ギャラリーステッカー等向け 指定チャンネル管理
@app_commands.guild_only()
@app_commands.default_permissions(manage_channels=True)
@app_commands.command(name ="add_workchannel_gallerysquare",description="チャンネルを画像処理のチェック対象に加えます(ホワイトリスト式の場合)")
async def add_workchannel_gallerysquare(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if (interaction.channel_id not in WHITELISTED_CHANNELS.gallerySquareChannels):
        logging.info(f"Add channel to the whitelist: {interaction.channel.name}@{interaction.channel.guild}({interaction.channel_id})")
        WHITELISTED_CHANNELS.gallerySquareChannels.append(interaction.channel_id)
    await interaction.followup.send(f"channel: #{interaction.channel.name} added!")
    ChannelsLoader.saveChannels(WHITELISTED_CHANNELS)

@app_commands.guild_only()
@app_commands.default_permissions(manage_channels=True)
@app_commands.command(name ="remove_workchannel_gallerysquare",description="チャンネルを画像処理のチェック対象から外します(チャンネルホワイトリスト有効の場合)")
async def remove_workchannel_gallerysquare(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if (interaction.channel_id in WHITELISTED_CHANNELS.gallerySquareChannels):
        logging.info(f"Remove channel from the whitelist: {interaction.channel.name}@{interaction.channel.guild}({interaction.channel_id})")
        WHITELISTED_CHANNELS.gallerySquareChannels.remove(interaction.channel_id)
    await interaction.followup.send(f"channel: #{interaction.channel.name} added!")
    ChannelsLoader.saveChannels(WHITELISTED_CHANNELS)

@app_commands.guild_only()
@app_commands.command(name ="get_workchannels_gallerysquare",description="画像処理を行えるチャンネル一覧を表示します(チャンネルホワイトリスト有効の場合)")
async def get_workchannels_gallerysquare(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    def get_is_guild(channel_id: int):
        channel = bot.get_channel(channel_id)
        return (channel) and (isinstance(channel, discord.TextChannel) or isinstance(channel, discord.Thread))
    channels = [bot.get_channel(channel_id) for channel_id in WHITELISTED_CHANNELS.gallerySquareChannels if get_is_guild(channel_id)]
    my_channels = [channel for channel in channels if (channel) and (channel.guild==interaction.guild)]
    message = "\n".join([f"[{c.name}](https://discord.com/channels/{c.guild.id}/{c.id})" for c in my_channels])
    await interaction.followup.send(message)
    
## ギャラリーステッカー用写真向け 指定チャンネル管理
@app_commands.guild_only()
@app_commands.default_permissions(manage_channels=True)
@app_commands.command(name ="add_workchannel_wide2square",description="チャンネルを画像処理のチェック対象に加えます(ホワイトリスト式の場合)")
async def add_workchannel_gallerywide2square(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if (interaction.channel_id not in WHITELISTED_CHANNELS.galleryWideToSquareChannels):
        logging.info(f"Add channel to the whitelist: {interaction.channel.name}@{interaction.channel.guild}({interaction.channel_id})")
        WHITELISTED_CHANNELS.galleryWideToSquareChannels.append(interaction.channel_id)
    await interaction.followup.send(f"channel: #{interaction.channel.name} added!")
    ChannelsLoader.saveChannels(WHITELISTED_CHANNELS)

@app_commands.guild_only()
@app_commands.default_permissions(manage_channels=True)
@app_commands.command(name ="remove_workchannel_wide2square",description="チャンネルを画像処理のチェック対象から外します(チャンネルホワイトリスト有効の場合)")
async def remove_workchannel_gallerywide2square(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if (interaction.channel_id in WHITELISTED_CHANNELS.galleryWideToSquareChannels):
        logging.info(f"Remove channel from the whitelist: {interaction.channel.name}@{interaction.channel.guild}({interaction.channel_id})")
        WHITELISTED_CHANNELS.galleryWideToSquareChannels.remove(interaction.channel_id)
    await interaction.followup.send(f"channel: #{interaction.channel.name} added!")
    ChannelsLoader.saveChannels(WHITELISTED_CHANNELS)

@app_commands.guild_only()
@app_commands.command(name ="get_workchannels_wide2square",description="画像処理を行えるチャンネル一覧を表示します(チャンネルホワイトリスト有効の場合)")
async def get_workchannels_gallerywide2square(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    def get_is_guild(channel_id: int):
        channel = bot.get_channel(channel_id)
        return (channel) and (isinstance(channel, discord.TextChannel) or isinstance(channel, discord.Thread))
    channels = [bot.get_channel(channel_id) for channel_id in WHITELISTED_CHANNELS.galleryWideToSquareChannels if get_is_guild(channel_id)]
    my_channels = [channel for channel in channels if (channel) and (channel.guild==interaction.guild)]
    message = "\n".join([f"[{c.name}](https://discord.com/channels/{c.guild.id}/{c.id})" for c in my_channels])
    await interaction.followup.send(message)

## ホワイトリスト有効化
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

## ホワイトリスト無効化
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
    if len(maskedToken) == 0:
        logging.fatal("トークンが未設定です, README.mdを見てBotのセットアップを行ってください")
    else:
        logging.info(f"Starting Bot with token: {maskedToken}")
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
    input("Press enter to continue")
