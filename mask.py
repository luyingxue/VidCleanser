"""
掩码生成模块
实现角落检测与掩码生成功能
"""
import os
import cv2
import numpy as np
from typing import Set, List, Tuple
from utils import get_logger


logger = get_logger(__name__)


def detect_corners(sample_frames: List[str], width: int, height: int, 
                  ratio_w: float, ratio_h: float) -> Set[str]:
    """
    检测视频角落中的水印位置
    
    Args:
        sample_frames: 抽样帧文件路径列表
        width: 视频宽度
        height: 视频高度
        ratio_w: 掩码宽度比例
        ratio_h: 掩码高度比例
        
    Returns:
        Set[str]: 检测到的角落集合 {'lt', 'rb'}
    """
    if not sample_frames:
        logger.warning("没有抽样帧，无法检测角落")
        return set()
    
    # 计算角落区域尺寸
    corner_w = int(width * ratio_w)
    corner_h = int(height * ratio_h)
    
    logger.info(f"开始检测角落水印，区域尺寸: {corner_w}x{corner_h}")
    
    # 计算左上和右下角落的分数
    lt_scores = []
    rb_scores = []
    
    for frame_path in sample_frames:
        try:
            # 读取帧 - 处理中文路径问题
            import numpy as np
            frame_data = np.fromfile(frame_path, dtype=np.uint8)
            frame = cv2.imdecode(frame_data, cv2.IMREAD_COLOR)
            if frame is None:
                logger.warning(f"无法读取帧: {frame_path}")
                continue
            
            # 转换为灰度图
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # 提取角落区域
            lt_region = gray[0:corner_h, 0:corner_w]
            rb_region = gray[height-corner_h:height, width-corner_w:width]
            
            # 计算左上角分数
            lt_score = _calculate_corner_score(lt_region)
            lt_scores.append(lt_score)
            
            # 计算右下角分数
            rb_score = _calculate_corner_score(rb_region)
            rb_scores.append(rb_score)
            
        except Exception as e:
            logger.warning(f"处理帧失败 {frame_path}: {e}")
            continue
    
    if not lt_scores or not rb_scores:
        logger.warning("没有有效的帧数据用于角落检测")
        return set()
    
    # 计算平均分数
    avg_lt_score = np.mean(lt_scores)
    avg_rb_score = np.mean(rb_scores)
    
    logger.info(f"角落检测分数 - 左上: {avg_lt_score:.3f}, 右下: {avg_rb_score:.3f}")
    
    # 应用阈值判断 - 降低阈值以检测更多水印
    threshold = 0.4
    detected_corners = set()
    
    if avg_lt_score >= threshold:
        detected_corners.add('lt')
        logger.info(f"检测到左上角水印（分数: {avg_lt_score:.3f}）")
    
    if avg_rb_score >= threshold:
        detected_corners.add('rb')
        logger.info(f"检测到右下角水印（分数: {avg_rb_score:.3f}）")
    
    # 如果都没有达到阈值，选择分数较高的
    if not detected_corners:
        if avg_lt_score > avg_rb_score:
            detected_corners.add('lt')
            logger.info(f"选择左上角（分数: {avg_lt_score:.3f}）")
        else:
            detected_corners.add('rb')
            logger.info(f"选择右下角（分数: {avg_rb_score:.3f}）")
    
    return detected_corners


def _calculate_corner_score(region: np.ndarray) -> float:
    """
    计算角落区域的分数
    
    Args:
        region: 角落区域图像
        
    Returns:
        float: 分数 (0-1)
    """
    if region.size == 0:
        return 0.0
    
    # 1. 亮度均值 (0-1)
    brightness = np.mean(region) / 255.0
    
    # 2. 边缘密度 (Canny 边缘像素比例)
    edges = cv2.Canny(region, 50, 150)
    edge_density = np.sum(edges > 0) / region.size
    
    # 3. 跨帧稳定性（这里简化为局部方差，实际应该比较相邻帧）
    # 使用局部方差作为稳定性指标
    kernel = np.ones((3, 3), np.float32) / 9
    local_mean = cv2.filter2D(region.astype(np.float32), -1, kernel)
    local_variance = np.mean((region.astype(np.float32) - local_mean) ** 2)
    stability = 1.0 / (1.0 + local_variance / 10000.0)  # 归一化到 0-1
    
    # 综合分数：0.4*亮度 + 0.4*稳定性 + 0.2*边缘密度
    score = 0.4 * brightness + 0.4 * stability + 0.2 * edge_density
    
    return min(1.0, max(0.0, score))


def build_mask(width: int, height: int, corners: Set[str], 
               ratio_w: float, ratio_h: float, pad_px: int = 8) -> str:
    """
    生成掩码图像
    
    Args:
        width: 视频宽度
        height: 视频高度
        corners: 检测到的角落集合
        ratio_w: 掩码宽度比例
        ratio_h: 掩码高度比例
        pad_px: 填充像素数
        
    Returns:
        str: 掩码文件路径
    """
    if not corners:
        logger.warning("没有检测到角落，生成空掩码")
        return _create_empty_mask(width, height)
    
    # 计算掩码区域尺寸
    mask_w = int(width * ratio_w)
    mask_h = int(height * ratio_h)
    
    logger.info(f"生成掩码，尺寸: {width}x{height}, 区域: {mask_w}x{mask_h}")
    
    # 创建全黑掩码
    mask = np.zeros((height, width), dtype=np.uint8)
    
    # 添加检测到的角落区域
    rectangles = []
    
    if 'lt' in corners:
        # 左上角
        x1, y1 = 0, 0
        x2, y2 = mask_w + pad_px, mask_h + pad_px
        rectangles.append((x1, y1, x2, y2))
        logger.info(f"添加左上角掩码: ({x1},{y1}) -> ({x2},{y2})")
    
    if 'rb' in corners:
        # 右下角
        x1, y1 = width - mask_w - pad_px, height - mask_h - pad_px
        x2, y2 = width, height
        rectangles.append((x1, y1, x2, y2))
        logger.info(f"添加右下角掩码: ({x1},{y1}) -> ({x2},{y2})")
    
    # 在掩码上绘制白色矩形
    for x1, y1, x2, y2 in rectangles:
        # 确保坐标在图像范围内
        x1 = max(0, min(x1, width))
        y1 = max(0, min(y1, height))
        x2 = max(0, min(x2, width))
        y2 = max(0, min(y2, height))
        
        if x2 > x1 and y2 > y1:
            mask[y1:y2, x1:x2] = 255
    
    # 保存掩码
    mask_path = "temp_mask.png"
    cv2.imwrite(mask_path, mask)
    
    logger.info(f"掩码已保存: {mask_path}")
    return mask_path


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
        if os.path.exists(mask_path):
            os.remove(mask_path)
            logger.debug(f"已清理掩码文件: {mask_path}")
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
