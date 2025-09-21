"""
固定掩码模块
根据视频分辨率直接使用预生成的掩码文件
"""
import os
import cv2
import numpy as np
from typing import Set, Tuple
from utils import get_logger


logger = get_logger(__name__)

# 预定义的视频类型和对应的分辨率
VIDEO_TYPES = {
    'jimeng': (832, 1120),    # 即梦视频分辨率
    'kling': (1152, 1760),    # 可灵视频分辨率
}

def detect_video_type(width: int, height: int) -> str:
    """
    根据视频分辨率判断视频类型
    
    Args:
        width: 视频宽度
        height: 视频高度
        
    Returns:
        str: 视频类型 ('jimeng', 'kling', 或 'unknown')
    """
    for video_type, (w, h) in VIDEO_TYPES.items():
        if width == w and height == h:
            return video_type
    
    logger.warning(f"未知视频分辨率: {width}x{height}")
    return 'unknown'

def get_fixed_mask(width: int, height: int) -> Tuple[Set[str], str]:
    """
    根据视频分辨率获取固定掩码
    
    Args:
        width: 视频宽度
        height: 视频高度
        
    Returns:
        Tuple[Set[str], str]: (检测到的角落集合, 掩码文件路径)
    """
    video_type = detect_video_type(width, height)
    
    if video_type == 'unknown':
        logger.warning(f"不支持的分辨率 {width}x{height}，返回空掩码")
        return set(), _create_empty_mask(width, height)
    
    # 构建掩码文件路径
    mask_path = f"masks/{video_type}_mask.png"
    
    if not os.path.exists(mask_path):
        logger.error(f"掩码文件不存在: {mask_path}")
        return set(), _create_empty_mask(width, height)
    
    # 验证掩码尺寸
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    if mask is None:
        logger.error(f"无法读取掩码文件: {mask_path}")
        return set(), _create_empty_mask(width, height)
    
    mask_height, mask_width = mask.shape
    if mask_width != width or mask_height != height:
        logger.error(f"掩码尺寸不匹配: 期望 {width}x{height}, 实际 {mask_width}x{mask_height}")
        return set(), _create_empty_mask(width, height)
    
    # 检测掩码中的白色区域（水印区域）
    detected_corners = set()
    
    # 检查左上角区域是否有水印
    if _has_watermark_in_region(mask, 'lt', width, height):
        detected_corners.add('lt')
        logger.info("检测到左上角水印")
    
    # 检查右下角区域是否有水印
    if _has_watermark_in_region(mask, 'rb', width, height):
        detected_corners.add('rb')
        logger.info("检测到右下角水印")
    
    logger.info(f"使用固定掩码: {mask_path}, 检测到角落: {detected_corners}")
    return detected_corners, mask_path

def _has_watermark_in_region(mask: np.ndarray, corner: str, width: int, height: int) -> bool:
    """
    检查指定角落区域是否有水印
    
    Args:
        mask: 掩码图像
        corner: 角落类型 'lt' 或 'rb'
        width: 图像宽度
        height: 图像高度
        
    Returns:
        bool: 是否有水印
    """
    # 定义搜索区域（角落的30%区域）
    search_ratio = 0.3
    search_w = int(width * search_ratio)
    search_h = int(height * search_ratio)
    
    if corner == 'lt':
        # 左上角搜索区域
        search_region = mask[0:search_h, 0:search_w]
    else:  # 'rb'
        # 右下角搜索区域
        search_region = mask[height-search_h:height, width-search_w:width]
    
    # 检查是否有白色像素
    white_pixels = np.sum(search_region == 255)
    return white_pixels > 0

def _create_empty_mask(width: int, height: int) -> str:
    """
    创建空掩码（全黑）
    
    Args:
        width: 宽度
        height: 高度
        
    Returns:
        str: 掩码文件路径
    """
    mask = np.zeros((height, width), dtype=np.uint8)
    mask_path = "temp_mask.png"
    cv2.imwrite(mask_path, mask)
    logger.info("创建空掩码")
    return mask_path

def validate_mask(mask_path: str) -> bool:
    """
    验证掩码文件是否有效
    
    Args:
        mask_path: 掩码文件路径
        
    Returns:
        bool: 掩码是否有效
    """
    if not os.path.exists(mask_path):
        return False
    
    try:
        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        if mask is None:
            return False
        
        # 检查是否有白色区域
        white_pixels = np.sum(mask == 255)
        return white_pixels > 0
        
    except Exception as e:
        logger.warning(f"验证掩码失败: {e}")
        return False

def cleanup_mask(mask_path: str) -> None:
    """
    清理掩码文件
    
    Args:
        mask_path: 掩码文件路径
    """
    try:
        if os.path.exists(mask_path) and mask_path.startswith("temp_"):
            os.remove(mask_path)
            logger.debug(f"已清理临时掩码文件: {mask_path}")
    except Exception as e:
        logger.warning(f"清理掩码文件失败: {e}")

def get_mask_info(mask_path: str) -> Tuple[int, int, int]:
    """
    获取掩码信息
    
    Args:
        mask_path: 掩码文件路径
        
    Returns:
        Tuple[int, int, int]: (宽度, 高度, 白色像素数)
    """
    try:
        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        if mask is None:
            return 0, 0, 0
        
        height, width = mask.shape
        white_pixels = np.sum(mask == 255)
        return width, height, white_pixels
        
    except Exception as e:
        logger.warning(f"获取掩码信息失败: {e}")
        return 0, 0, 0
