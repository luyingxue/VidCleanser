"""
FFmpeg 工具封装模块
提供视频信息获取、帧抽样、帧提取、视频合成等功能
"""
import os
import subprocess
import logging
from typing import List, Tuple
from utils import get_logger

logger = get_logger(__name__)


def check_ffmpeg_available() -> bool:
    """
    检查 FFmpeg 和 FFprobe 是否可用
    
    Returns:
        bool: 是否可用
    """
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)
        logger.info("FFmpeg 和 FFprobe 可用")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("FFmpeg 或 FFprobe 不可用")
        return False


def probe_video(video_path: str) -> Tuple[int, int, float]:
    """
    获取视频信息
    
    Args:
        video_path: 视频文件路径
        
    Returns:
        Tuple[int, int, float]: (宽度, 高度, 帧率)
        
    Raises:
        RuntimeError: 当 ffprobe 执行失败时
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,r_frame_rate',
            '-of', 'csv=p=0',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout.strip()
        
        if not output:
            raise RuntimeError("ffprobe 输出为空")
        
        # 解析输出：width,height,r_frame_rate
        parts = output.split(',')
        if len(parts) != 3:
            raise RuntimeError(f"ffprobe 输出格式错误: {output}")
        
        width = int(parts[0])
        height = int(parts[1])
        
        # 解析帧率 (格式: "60/1" 或 "30/1")
        fps_str = parts[2]
        if '/' in fps_str:
            num, den = fps_str.split('/')
            fps = float(num) / float(den)
        else:
            fps = float(fps_str)
        
        logger.info(f"视频信息: {width}x{height} @ {fps:.2f}fps")
        return width, height, fps
        
    except subprocess.CalledProcessError as e:
        logger.error(f"ffprobe 执行失败: {e.stderr}")
        raise RuntimeError(f"ffprobe 执行失败: {e.stderr}")
    except Exception as e:
        logger.error(f"解析视频信息失败: {e}")
        raise RuntimeError(f"解析视频信息失败: {e}")


def extract_frames(video_path: str, output_dir: str, fps: float) -> None:
    """
    提取视频的所有帧
    
    Args:
        video_path: 视频文件路径
        output_dir: 输出目录
        fps: 帧率
        
    Raises:
        RuntimeError: 当 ffmpeg 执行失败时
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        cmd = f'ffmpeg -hide_banner -loglevel error -y -i "{video_path}" -vf fps={fps} -f image2 "{os.path.join(output_dir, "%06d.png")}"'
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=True, encoding='utf-8', errors='ignore')
        logger.info(f"成功提取帧到 {output_dir}")
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg 提取帧失败: {e.stderr}")
        raise RuntimeError(f"ffmpeg 提取帧失败: {e.stderr}")
    except Exception as e:
        logger.error(f"提取帧异常: {e}")
        raise RuntimeError(f"提取帧异常: {e}")


def assemble_video(frames_dir: str, fps: float, output_path: str) -> int:
    """
    将帧序列合成为视频
    
    Args:
        frames_dir: 帧目录
        fps: 帧率
        output_path: 输出视频路径
        
    Returns:
        int: 返回码
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cmd = f'ffmpeg -hide_banner -loglevel error -y -framerate {fps} -i "{os.path.join(frames_dir, "%06d.png")}" -c:v libx264 -pix_fmt yuv420p "{output_path}"'
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=True, encoding='utf-8', errors='ignore')
        logger.info(f"成功合成视频: {output_path}")
        return 0
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg 合成视频失败: {e.stderr}")
        return 1
    except Exception as e:
        logger.error(f"合成视频异常: {e}")
        return 1


def cleanup_temp_files(file_paths: List[str]) -> None:
    """
    清理临时文件
    
    Args:
        file_paths: 文件路径列表
    """
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.warning(f"清理文件失败 {file_path}: {e}")


def get_frame_count(frames_dir: str) -> int:
    """
    获取帧目录中的帧数
    
    Args:
        frames_dir: 帧目录
        
    Returns:
        int: 帧数
    """
    try:
        count = 0
        for filename in os.listdir(frames_dir):
            if filename.endswith('.png'):
                count += 1
        return count
    except Exception as e:
        logger.warning(f"获取帧数失败: {e}")
        return 0
