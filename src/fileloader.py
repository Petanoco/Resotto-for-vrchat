from dataclasses import dataclass, field
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
    DIRECTORY_NAME: ClassVar[str] = "config"
    FILE_NAME: ClassVar[str] = "config.json"
    FILE_PATH: ClassVar[str] = os.path.join(FileLoader.ROOT_DIRECTORY, DIRECTORY_NAME, FILE_NAME)
    
    token: str = ""
    presence: str = "aaa"
    target_resolution: int = 2048
    max_file_count: int = 4
    log_level:str = "INFO"
    log_level_value: int = getLevelName(log_level)
    quality: int = 5
    resampling_value: Resampling = Resampling.LANCZOS
    use_timestamped_logfilename:bool = False

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
            with open(Config.FILE_PATH, 'r', encoding='utf-8') as file:
                data = Config(**json.load(file))
                data.log_level_value = getLevelName(data.log_level)
                data.resampling_value = Config.getResamplingValue(data.quality)
                return data
        except FileNotFoundError:
            getLogger().critical("設定ファイルが見つかりません")
            raise
        except:
            getLogger().critical("設定ファイルの読み込みに失敗しました")
            raise


@dataclass
class ChannelsLoader:
    DIRECTORY_NAME: ClassVar[str] = "config"
    FILE_NAME: ClassVar[str] = "target_channels.json"
    FILE_PATH: ClassVar[str] = os.path.join(FileLoader.ROOT_DIRECTORY, DIRECTORY_NAME, FILE_NAME)
    
    @staticmethod
    def saveChannels(channel_ids: list[int]):
        try:
            with open(ChannelsLoader.FILE_PATH, "w", encoding="utf-8") as file:
                json.dump(channel_ids, file, ensure_ascii=False, indent=4)
        except PermissionError:
            logging.error("権限エラー: 設定ファイルを保存できません")
        except:
            logging.error("設定ファイルの保存に失敗しました")
            raise
            
    @staticmethod
    def loadChannels() -> list[int]:
        try:
            with open(ChannelsLoader.FILE_PATH, "r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            return list[int]()
    
    @staticmethod
    def cleanupChannels(channel_ids: list[int], bot: discord.Client) -> list[int]:
        all_channel_ids = [channel.id for channel in bot.get_all_channels()]
        valid_channel_ids = [id for id in channel_ids if (id in all_channel_ids)]
        return valid_channel_ids

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
