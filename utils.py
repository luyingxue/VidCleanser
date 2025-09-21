"""
公共工具函数模块
提供日志、路径、文件锁/标记、排序等通用功能
"""
import os
import logging
import time
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime


def setup_logging(log_level: str = "info", log_file: str = "logs/app.log") -> None:
    """
    设置日志系统
    
    Args:
        log_level: 日志级别
        log_file: 日志文件路径
    """
    # 创建日志目录
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 设置日志级别
    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warn": logging.WARNING,
        "error": logging.ERROR
    }
    level = level_map.get(log_level.lower(), logging.INFO)
    
    # 配置日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 配置根日志器
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def get_logger(name: str) -> logging.Logger:
    """
    获取日志器
    
    Args:
        name: 日志器名称
        
    Returns:
        logging.Logger: 日志器对象
    """
    return logging.getLogger(name)


def find_mp4_files(directory: str) -> List[str]:
    """
    递归查找目录下的所有 .mp4 文件
    
    Args:
        directory: 搜索目录
        
    Returns:
        List[str]: .mp4 文件路径列表（按文件名排序）
    """
    mp4_files = []
    if not os.path.exists(directory):
        return mp4_files
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.mp4'):
                full_path = os.path.join(root, file)
                mp4_files.append(full_path)
    
    # 按文件名排序
    mp4_files.sort()
    return mp4_files


def is_processing_file(file_path: str) -> bool:
    """
    检查文件是否正在处理中
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 是否正在处理
    """
    # 检查是否有 .processing 扩展名
    if file_path.endswith('.processing'):
        return True
    
    # 检查是否在 work 目录中
    work_dir = "work"
    if work_dir in file_path.split(os.sep):
        return True
    
    return False


def is_temp_file(file_path: str) -> bool:
    """
    检查是否为临时文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 是否为临时文件
    """
    temp_extensions = ['.tmp', '.temp', '.processing', '.cleaned']
    return any(file_path.endswith(ext) for ext in temp_extensions)


def create_work_directory(video_name: str, temp_dir: str = "work") -> str:
    """
    为视频创建工作目录
    
    Args:
        video_name: 视频文件名（不含扩展名）
        temp_dir: 临时目录路径
        
    Returns:
        str: 工作目录路径
    """
    work_dir = os.path.join(temp_dir, video_name)
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(os.path.join(work_dir, "frames"), exist_ok=True)
    os.makedirs(os.path.join(work_dir, "restored"), exist_ok=True)
    return work_dir


def cleanup_work_directory(work_dir: str) -> None:
    """
    清理工作目录
    
    Args:
        work_dir: 工作目录路径
    """
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)


def move_video_to_work(video_path: str, work_dir: str) -> str:
    """
    将视频移动到工作目录
    
    Args:
        video_path: 原视频路径
        work_dir: 工作目录
        
    Returns:
        str: 工作目录中的视频路径
    """
    work_video_path = os.path.join(work_dir, "input.mp4")
    shutil.move(video_path, work_video_path)
    return work_video_path


def copy_video_to_work(video_path: str, work_dir: str) -> str:
    """
    将视频复制到工作目录（保留原文件）
    
    Args:
        video_path: 原视频路径
        work_dir: 工作目录
        
    Returns:
        str: 工作目录中的视频路径
    """
    work_video_path = os.path.join(work_dir, "input.mp4")
    shutil.copy2(video_path, work_video_path)
    return work_video_path


def move_video_back(video_path: str, original_path: str) -> None:
    """
    将视频移回原位置（失败时使用）
    
    Args:
        video_path: 工作目录中的视频路径
        original_path: 原位置路径
    """
    if os.path.exists(video_path):
        shutil.move(video_path, original_path)


def get_video_name(video_path: str) -> str:
    """
    获取视频文件名（不含扩展名）
    
    Args:
        video_path: 视频路径
        
    Returns:
        str: 视频文件名
    """
    return os.path.splitext(os.path.basename(video_path))[0]


def format_duration(seconds: float) -> str:
    """
    格式化时长显示
    
    Args:
        seconds: 秒数
        
    Returns:
        str: 格式化的时长字符串
    """
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}分{secs:.1f}秒"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}小时{minutes}分{secs:.1f}秒"


def ensure_directory(directory: str) -> None:
    """
    确保目录存在
    
    Args:
        directory: 目录路径
    """
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def get_file_size(file_path: str) -> int:
    """
    获取文件大小（字节）
    
    Args:
        file_path: 文件路径
        
    Returns:
        int: 文件大小，文件不存在返回 0
    """
    if os.path.exists(file_path):
        return os.path.getsize(file_path)
    return 0


def is_valid_video_file(file_path: str) -> bool:
    """
    检查是否为有效的视频文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 是否为有效视频文件
    """
    if not os.path.exists(file_path):
        return False
    
    # 检查文件大小
    if get_file_size(file_path) == 0:
        return False
    
    # 检查扩展名
    if not file_path.lower().endswith('.mp4'):
        return False
    
    return True
