"""
配置文件管理模块
加载 config.yaml 并校验配置参数，提供默认值
"""
import os
import yaml
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class Config:
    """配置数据类"""
    input_dir: str
    output_dir: str
    temp_dir: str
    lama_api_url: str
    api_workers: int
    scan_interval_sec: int
    log_level: str
    mask_path: str


def load_config(config_path: str = "config.yaml") -> Config:
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        Config: 配置对象
    """
    # 默认配置
    default_config = {
        "input_dir": "E:/videos_in",
        "output_dir": "E:/videos_out",
        "temp_dir": "E:/videos_temp",
        "lama_api_url": "http://127.0.0.1:8080/inpaint",
        "api_workers": 3,
        "scan_interval_sec": 10,
        "log_level": "info",
        "mask_path": "E:/videos_in/jimeng_mask.png"
    }
    
    # 如果配置文件存在，加载并合并
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f) or {}
            # 合并配置，用户配置覆盖默认配置
            for key, value in user_config.items():
                if key in default_config:
                    default_config[key] = value
        except Exception as e:
            print(f"警告：读取配置文件失败，使用默认配置: {e}")
    
    # 校验配置
    _validate_config(default_config)
    
    return Config(
        input_dir=default_config["input_dir"],
        output_dir=default_config["output_dir"],
        temp_dir=default_config["temp_dir"],
        lama_api_url=default_config["lama_api_url"],
        api_workers=default_config["api_workers"],
        scan_interval_sec=default_config["scan_interval_sec"],
        log_level=default_config["log_level"],
        mask_path=default_config["mask_path"]
    )


def _validate_config(config: dict) -> None:
    """
    校验配置参数
    
    Args:
        config: 配置字典
    """
    # 校验路径
    input_dir = config.get("input_dir", "")
    output_dir = config.get("output_dir", "")
    
    if not input_dir:
        raise ValueError("input_dir 不能为空")
    if not output_dir:
        raise ValueError("output_dir 不能为空")
    
    # 校验数值范围
    api_workers = config.get("api_workers", 3)
    if not isinstance(api_workers, int) or api_workers < 1 or api_workers > 10:
        raise ValueError("api_workers 必须是 1-10 之间的整数")
    
    scan_interval_sec = config.get("scan_interval_sec", 10)
    if not isinstance(scan_interval_sec, int) or scan_interval_sec < 1:
        raise ValueError("scan_interval_sec 必须是正整数")
    
    # 校验字符串选项
    log_level = config.get("log_level", "info")
    if log_level not in ["debug", "info", "warn", "error"]:
        raise ValueError("log_level 必须是 'debug', 'info', 'warn' 或 'error'")
    
    # 校验掩码文件路径
    mask_path = config.get("mask_path", "")
    if not mask_path:
        raise ValueError("mask_path 不能为空")
