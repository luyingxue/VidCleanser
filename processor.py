"""
单视频处理管线模块
实现完整的视频处理流程：拆帧 → 修复 → 合成 → 清理
"""
import os
import time
import shutil
from pathlib import Path
from typing import Optional, Tuple

from config import Config
from utils import (
    get_logger, create_work_directory, cleanup_work_directory,
    move_video_to_work, copy_video_to_work, move_video_back, get_video_name,
    format_duration, ensure_directory, is_valid_video_file
)
from ffmpeg_utils import (
    probe_video, sample_frames, extract_frames, assemble_video,
    cleanup_temp_files, get_frame_count, check_ffmpeg_available
)
from mask import detect_corners, build_mask, cleanup_mask, validate_mask
from api_client import IOPaintClient


logger = get_logger(__name__)


class VideoProcessor:
    """视频处理器"""
    
    def __init__(self, config: Config):
        """
        初始化处理器
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.api_client = IOPaintClient(
            config.lama_api_url, 
            config.api_workers
        )
        
        # 确保输出目录存在
        ensure_directory(config.output_dir)
        
        logger.info("视频处理器初始化完成")
    
    def process_video(self, video_path: str) -> bool:
        """
        处理单个视频
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            bool: 处理是否成功
        """
        start_time = time.time()
        video_name = get_video_name(video_path)
        
        logger.info(f"开始处理视频: {video_name}")
        
        # 验证视频文件
        if not is_valid_video_file(video_path):
            logger.error(f"无效的视频文件: {video_path}")
            return False
        
        # 创建工作目录
        work_dir = create_work_directory(video_name, self.config.temp_dir)
        work_video_path = os.path.join(work_dir, "input.mp4")
        
        try:
            # 1. 复制视频到工作目录（保留原文件）
            logger.info("复制视频到工作目录")
            copy_video_to_work(video_path, work_dir)
            
            # 2. 获取视频信息
            logger.info("获取视频信息")
            width, height, fps = probe_video(work_video_path)
            
            # 3. 抽样帧进行角落检测
            logger.info("抽样帧进行角落检测")
            sample_dir = os.path.join(work_dir, "samples")
            os.makedirs(sample_dir, exist_ok=True)
            
            sample_frame_paths = sample_frames(
                work_video_path, 
                self.config.sample_frames, 
                sample_dir
            )
            
            if not sample_frame_paths:
                logger.error("抽样帧失败")
                return False
            
            # 4. 检测角落水印
            logger.info("检测角落水印")
            corners = detect_corners(
                sample_frame_paths, 
                width, height,
                self.config.mask_ratio_w, 
                self.config.mask_ratio_h
            )
            
            if not corners:
                logger.warning("未检测到水印，跳过处理")
                return True  # 视为成功，无需处理
            
            logger.info(f"检测到水印位置: {corners}")
            
            # 5. 生成掩码
            logger.info("生成掩码")
            mask_path = build_mask(
                width, height, corners,
                self.config.mask_ratio_w, 
                self.config.mask_ratio_h
            )
            
            if not validate_mask(mask_path):
                logger.error("掩码生成失败")
                return False
            
            # 6. 提取所有帧
            logger.info("提取所有帧")
            frames_dir = os.path.join(work_dir, "frames")
            extract_frames(work_video_path, frames_dir, fps)
            
            frame_count = get_frame_count(frames_dir)
            if frame_count == 0:
                logger.error("帧提取失败")
                return False
            
            logger.info(f"成功提取 {frame_count} 帧")
            
            # 7. 修复帧
            logger.info("开始修复帧")
            restored_dir = os.path.join(work_dir, "restored")
            
            if not self.api_client.repair_frames(frames_dir, mask_path, restored_dir):
                logger.error("帧修复失败")
                return False
            
            # 8. 合成视频
            logger.info("合成视频")
            output_filename = f"{video_name}_cleaned.mp4"
            output_path = os.path.join(self.config.output_dir, output_filename)
            
            return_code = assemble_video(restored_dir, fps, output_path)
            if return_code != 0:
                logger.error("视频合成失败")
                return False
            
            # 验证输出文件
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                logger.error("输出视频文件无效")
                return False
            
            # 9. 清理工作目录
            logger.info("清理工作目录")
            cleanup_work_directory(work_dir)
            cleanup_mask(mask_path)
            
            # 10. 删除原视频
            if os.path.exists(video_path):
                os.remove(video_path)
                logger.info("已删除原视频")
            
            # 计算处理时间
            duration = time.time() - start_time
            logger.info(f"视频处理完成: {video_name}, 耗时: {format_duration(duration)}")
            
            return True
            
        except Exception as e:
            logger.error(f"处理视频异常: {video_name}, {e}")
            
            # 失败时清理工作目录，但保留原视频
            try:
                cleanup_work_directory(work_dir)
                # 如果原视频被移动了，移回原位置
                if os.path.exists(work_video_path) and not os.path.exists(video_path):
                    move_video_back(work_video_path, video_path)
            except Exception as cleanup_error:
                logger.error(f"清理失败: {cleanup_error}")
            
            return False
        
        finally:
            # 清理抽样帧
            try:
                cleanup_temp_files(sample_frame_paths)
            except Exception as e:
                logger.warning(f"清理抽样帧失败: {e}")
    
    def test_api_connection(self) -> bool:
        """
        测试 API 连接
        
        Returns:
            bool: 连接是否成功
        """
        return self.api_client.test_connection()
    
    def close(self):
        """关闭处理器"""
        self.api_client.close()
        logger.debug("视频处理器已关闭")


def process_single_video(video_path: str, config: Config) -> bool:
    """
    处理单个视频（便捷函数）
    
    Args:
        video_path: 视频文件路径
        config: 配置对象
        
    Returns:
        bool: 处理是否成功
    """
    processor = VideoProcessor(config)
    try:
        return processor.process_video(video_path)
    finally:
        processor.close()


def validate_environment(config: Config) -> Tuple[bool, str]:
    """
    验证运行环境
    
    Args:
        config: 配置对象
        
    Returns:
        Tuple[bool, str]: (是否有效, 错误信息)
    """
    # 检查 FFmpeg
    if not check_ffmpeg_available():
        return False, "FFmpeg 不可用，请确保已安装并添加到 PATH"
    
    # 检查输入目录
    if not os.path.exists(config.input_dir):
        return False, f"输入目录不存在: {config.input_dir}"
    
    # 检查输出目录（尝试创建）
    try:
        ensure_directory(config.output_dir)
    except Exception as e:
        return False, f"无法创建输出目录: {e}"
    
    # 检查 API 连接
    processor = VideoProcessor(config)
    try:
        if not processor.test_api_connection():
            return False, f"无法连接到 IOPaint API: {config.lama_api_url}"
    finally:
        processor.close()
    
    return True, "环境验证通过"
