"""
FFmpeg 工具模块
封装 ffprobe、拆帧、合成等 FFmpeg 相关操作
"""
import os
import subprocess
import tempfile
import shutil
from typing import Tuple, List, Optional
from pathlib import Path
from utils import get_logger


logger = get_logger(__name__)


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
        
        # 解析帧率 (例如 "30/1" -> 30.0)
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


def sample_frames(video_path: str, n_frames: int, tmp_dir: str) -> List[str]:
    """
    从视频中抽样指定数量的帧
    
    Args:
        video_path: 视频文件路径
        n_frames: 抽样帧数
        tmp_dir: 临时目录
        
    Returns:
        List[str]: 抽样帧文件路径列表
        
    Raises:
        RuntimeError: 当 ffmpeg 执行失败时
    """
    try:
        # 确保临时目录存在
        os.makedirs(tmp_dir, exist_ok=True)
        
        # 使用 ffmpeg 抽样帧
        # 使用更简单的抽样策略：每隔一定帧数取一帧
        # 处理中文路径问题，使用 shell=True
        cmd = f'ffmpeg -hide_banner -loglevel error -y -i "{video_path}" -vf fps=1/{max(1, n_frames)} -vframes {n_frames} -f image2 "{os.path.join(tmp_dir, "sample_%03d.png")}"'
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=True, encoding='utf-8', errors='ignore')
        
        # 查找生成的帧文件
        frame_files = []
        for i in range(1, n_frames + 1):  # FFmpeg 从 001 开始编号
            frame_path = os.path.join(tmp_dir, f'sample_{i:03d}.png')
            if os.path.exists(frame_path):
                frame_files.append(frame_path)
        
        # 如果按序号查找失败，尝试查找所有 .png 文件
        if not frame_files:
            for filename in os.listdir(tmp_dir):
                if filename.endswith('.png'):
                    frame_path = os.path.join(tmp_dir, filename)
                    frame_files.append(frame_path)
        
        if not frame_files:
            raise RuntimeError("未生成任何抽样帧")
        
        # 按文件名排序
        frame_files.sort()
        
        logger.info(f"成功抽样 {len(frame_files)} 帧")
        return frame_files
        
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg 抽样帧失败: {e.stderr}")
        raise RuntimeError(f"ffmpeg 抽样帧失败: {e.stderr}")
    except Exception as e:
        logger.error(f"抽样帧失败: {e}")
        raise RuntimeError(f"抽样帧失败: {e}")


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
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 处理中文路径问题，使用 shell=True
        cmd = f'ffmpeg -hide_banner -loglevel error -y -i "{video_path}" -vf fps={fps} -f image2 "{os.path.join(output_dir, "%06d.png")}"'
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=True, encoding='utf-8', errors='ignore')
        
        # 检查是否生成了帧文件
        frame_files = [f for f in os.listdir(output_dir) if f.endswith('.png')]
        if not frame_files:
            raise RuntimeError("未生成任何帧文件")
        
        logger.info(f"成功提取 {len(frame_files)} 帧到 {output_dir}")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg 提取帧失败: {e.stderr}")
        raise RuntimeError(f"ffmpeg 提取帧失败: {e.stderr}")
    except Exception as e:
        logger.error(f"提取帧失败: {e}")
        raise RuntimeError(f"提取帧失败: {e}")


def assemble_video(frames_dir: str, fps: float, output_path: str) -> int:
    """
    将帧序列合成为视频
    
    Args:
        frames_dir: 帧文件目录
        fps: 帧率
        output_path: 输出视频路径
        
    Returns:
        int: ffmpeg 返回码（0 表示成功）
    """
    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        cmd = [
            'ffmpeg',
            '-hide_banner',
            '-loglevel', 'error',
            '-y',
            '-framerate', str(fps),
            '-i', os.path.join(frames_dir, '%06d.png'),
            '-c:v', 'libx264',
            '-crf', '18',
            '-pix_fmt', 'yuv420p',
            '-an',  # 无音频
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"成功合成视频: {output_path}")
        else:
            logger.error(f"ffmpeg 合成视频失败: {result.stderr}")
        
        return result.returncode
        
    except Exception as e:
        logger.error(f"合成视频失败: {e}")
        return 1


def check_ffmpeg_available() -> bool:
    """
    检查 FFmpeg 是否可用
    
    Returns:
        bool: FFmpeg 是否可用
    """
    try:
        # 检查 ffmpeg
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, check=True)
        
        # 检查 ffprobe
        result = subprocess.run(['ffprobe', '-version'], 
                              capture_output=True, text=True, check=True)
        
        logger.info("FFmpeg 和 FFprobe 可用")
        return True
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("FFmpeg 或 FFprobe 不可用，请确保已安装并添加到 PATH")
        return False


def cleanup_temp_files(file_paths: List[str]) -> None:
    """
    清理临时文件
    
    Args:
        file_paths: 要清理的文件路径列表
    """
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.warning(f"清理临时文件失败 {file_path}: {e}")


def get_frame_count(frames_dir: str) -> int:
    """
    获取帧目录中的帧数量
    
    Args:
        frames_dir: 帧目录
        
    Returns:
        int: 帧数量
    """
    if not os.path.exists(frames_dir):
        return 0
    
    frame_files = [f for f in os.listdir(frames_dir) if f.endswith('.png')]
    return len(frame_files)
