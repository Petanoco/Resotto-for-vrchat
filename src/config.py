from dataclasses import dataclass, field
from logging import getLogger, getLevelName
import json
from PIL.Image import Resampling

@dataclass
class Config:
    token: str = ""
    is_whitelisted: bool = True
    presence: str = "aaa"
    target_resolution: int = 2048
    max_file_count: int = 4
    log_level:str = "INFO"
    log_level_value: int = getLevelName(log_level)
    ignore_user_ids: list[str] = field(default_factory=list)
    quality: int = 5
    resampling_value: Resampling = Resampling.LANCZOS

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
    def load(file_path: str) -> 'Config':
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
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
