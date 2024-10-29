from dataclasses import dataclass, field, asdict
from logging import getLogger, getLevelName
import json
from PIL.Image import Resampling
from typing import ClassVar
import os
import sys
import logging
import discord
from discord.ext import commands

class FileLoader:
    ROOT_DIRECTORY = os.path.dirname(sys.executable) if hasattr(sys, '_MEIPASS') else os.path.dirname(os.path.abspath(__file__))

@dataclass
class Config:
    token: str = ""
    presence: str = "aaa"
    target_resolution: int = 2048
    max_file_count: int = 4
    log_level:str = "INFO"
    log_level_value: int = getLevelName(log_level)
    quality: int = 5
    resampling_value: Resampling = Resampling.LANCZOS
    use_timestamped_logfilename:bool = False
    allow_direct:bool = True

@dataclass
class ConfigLoader:
    DIRECTORY_NAME: ClassVar[str] = "config"
    FILE_NAME: ClassVar[str] = "config.json"
    FILE_PATH: ClassVar[str] = os.path.join(FileLoader.ROOT_DIRECTORY, DIRECTORY_NAME, FILE_NAME)

    @staticmethod
    def getResamplingValue(quality: int) -> Resampling:
        if (quality>=5):
            return Resampling.LANCZOS
        elif(quality==4):
            return Resampling.BICUBIC
        elif(quality==3):
            return Resampling.HAMMING
        elif(quality==2):
            return Resampling.BILINEAR
        elif(quality==1):
            return Resampling.BOX
        else:
            return Resampling.NEAREST
        
    @staticmethod
    def load() -> 'Config':
        try:
            with open(ConfigLoader.FILE_PATH, 'r', encoding='utf-8') as file:
                data = Config(**json.load(file))
                data.log_level_value = getLevelName(data.log_level)
                data.resampling_value = ConfigLoader.getResamplingValue(data.quality)
                return data
        except FileNotFoundError:
            getLogger().critical("設定ファイルが見つかりません")
            raise
        except:
            getLogger().critical("設定ファイルの読み込みに失敗しました")
            raise

@dataclass
class SavedChannels:
    imageloaderChannels: list[int] = field(default_factory=list)
    galleryWideChannels: list[int] = field(default_factory=list)
    gallerySquareChannels: list[int] = field(default_factory=list)
    galleryWideToSquareChannels: list[int] = field(default_factory=list)

@dataclass
class ChannelsLoader:
    DIRECTORY_NAME: ClassVar[str] = "config"
    FILE_NAME: ClassVar[str] = "target_channels.json"
    FILE_PATH: ClassVar[str] = os.path.join(FileLoader.ROOT_DIRECTORY, DIRECTORY_NAME, FILE_NAME)
    
    @staticmethod
    def saveChannels(savedChannels: SavedChannels):
        try:
            with open(ChannelsLoader.FILE_PATH, "w", encoding="utf-8") as file:
                json.dump(asdict(savedChannels), file, ensure_ascii=False, indent=4)
        except PermissionError:
            logging.error("権限エラー: 設定ファイルを保存できません")
        except:
            logging.error("設定ファイルの保存に失敗しました")
            raise
            
    @staticmethod
    def loadChannels() -> SavedChannels:
        try:
            with open(ChannelsLoader.FILE_PATH, "r", encoding="utf-8") as file:
                return SavedChannels(**json.load(file))
        except FileNotFoundError:
            return SavedChannels()

@dataclass
class WhitelistableGuildsLoader:
    DIRECTORY_NAME: ClassVar[str] = "config"
    FILE_NAME: ClassVar[str] = "whitelistable_guilds.json"
    FILE_PATH: ClassVar[str] = os.path.join(FileLoader.ROOT_DIRECTORY, DIRECTORY_NAME, FILE_NAME)
    
    @staticmethod
    def saveGuilds(guild_ids: list[int]):
        try:
            with open(WhitelistableGuildsLoader.FILE_PATH, "w", encoding="utf-8") as file:
                json.dump(guild_ids, file, ensure_ascii=False, indent=4)
        except PermissionError:
            logging.error("権限エラー: 設定ファイルを保存できません")
        except:
            logging.error("設定ファイルの保存に失敗しました")
            raise
            
    @staticmethod
    def loadGuilds() -> list[int]:
        try:
            with open(WhitelistableGuildsLoader.FILE_PATH, "r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            return list[int]()
    
    @staticmethod
    def cleanupGuilds(guild_ids: list[int], bot: discord.Client) -> list[int]:
        all_guild_ids = [guild.id for guild in bot.guilds()]
        valid_guild_ids = [id for id in guild_ids if (id in all_guild_ids)]
        return valid_guild_ids
