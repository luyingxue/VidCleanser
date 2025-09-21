"""
目录轮询与任务队列模块
监控输入目录，发现新视频并串行处理
"""
import os
import time
from typing import List, Optional
from pathlib import Path

from config import Config
from utils import (
    get_logger, find_mp4_files, is_processing_file, 
    is_temp_file, is_valid_video_file
)
from processor import VideoProcessor


logger = get_logger(__name__)


class VideoWatcher:
    """视频监控器"""
    
    def __init__(self, config: Config):
        """
        初始化监控器
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.processor = VideoProcessor(config)
        self.running = False
        
        logger.info(f"视频监控器初始化完成，监控目录: {config.input_dir}")
    
    def start(self):
        """开始监控"""
        self.running = True
        logger.info("开始监控视频文件")
        
        try:
            while self.running:
                self._scan_and_process()
                time.sleep(self.config.scan_interval_sec)
        except KeyboardInterrupt:
            logger.info("收到中断信号，停止监控")
        except Exception as e:
            logger.error(f"监控异常: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """停止监控"""
        self.running = False
        self.processor.close()
        logger.info("视频监控器已停止")
    
    def _scan_and_process(self):
        """
        扫描目录并处理视频
        严格串行：一次只处理一个视频
        """
        try:
            # 查找所有 .mp4 文件
            video_files = find_mp4_files(self.config.input_dir)
            
            if not video_files:
                logger.debug("未发现视频文件")
                return
            
            logger.debug(f"发现 {len(video_files)} 个视频文件")
            
            # 按文件名排序，确保处理顺序一致
            video_files.sort()
            
            # 找到第一个需要处理的视频
            video_to_process = self._find_next_video(video_files)
            
            if video_to_process:
                logger.info(f"开始处理视频: {os.path.basename(video_to_process)}")
                self._process_video(video_to_process)
            else:
                logger.debug("没有需要处理的视频")
                
        except Exception as e:
            logger.error(f"扫描处理异常: {e}")
    
    def _find_next_video(self, video_files: List[str]) -> Optional[str]:
        """
        找到下一个需要处理的视频
        
        Args:
            video_files: 视频文件列表
            
        Returns:
            Optional[str]: 下一个要处理的视频路径，如果没有则返回 None
        """
        for video_path in video_files:
            # 检查文件是否有效
            if not is_valid_video_file(video_path):
                logger.debug(f"跳过无效文件: {video_path}")
                continue
            
            # 检查是否正在处理
            if is_processing_file(video_path):
                logger.debug(f"跳过正在处理的文件: {video_path}")
                continue
            
            # 检查是否为临时文件
            if is_temp_file(video_path):
                logger.debug(f"跳过临时文件: {video_path}")
                continue
            
            # 找到第一个符合条件的视频
            logger.info(f"选择处理视频: {os.path.basename(video_path)}")
            return video_path
        
        return None
    
    def _process_video(self, video_path: str):
        """
        处理单个视频
        
        Args:
            video_path: 视频文件路径
        """
        start_time = time.time()
        video_name = os.path.basename(video_path)
        
        try:
            # 标记为正在处理（通过移动到 work 目录实现）
            logger.info(f"开始处理: {video_name}")
            
            # 调用处理器处理视频
            success = self.processor.process_video(video_path)
            
            # 计算处理时间
            duration = time.time() - start_time
            
            if success:
                logger.info(f"视频处理成功: {video_name}, 耗时: {duration:.1f}秒")
            else:
                logger.error(f"视频处理失败: {video_name}, 耗时: {duration:.1f}秒")
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"处理视频异常: {video_name}, 耗时: {duration:.1f}秒, 错误: {e}")
    
    def process_single_video(self, video_path: str) -> bool:
        """
        处理单个视频（外部调用）
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            bool: 处理是否成功
        """
        if not os.path.exists(video_path):
            logger.error(f"视频文件不存在: {video_path}")
            return False
        
        if not is_valid_video_file(video_path):
            logger.error(f"无效的视频文件: {video_path}")
            return False
        
        logger.info(f"外部调用处理视频: {video_path}")
        return self.processor.process_video(video_path)
    
    def get_status(self) -> dict:
        """
        获取监控器状态
        
        Returns:
            dict: 状态信息
        """
        video_files = find_mp4_files(self.config.input_dir)
        valid_files = [f for f in video_files if is_valid_video_file(f)]
        processing_files = [f for f in video_files if is_processing_file(f)]
        
        return {
            "running": self.running,
            "input_dir": self.config.input_dir,
            "output_dir": self.config.output_dir,
            "total_videos": len(video_files),
            "valid_videos": len(valid_files),
            "processing_videos": len(processing_files),
            "scan_interval": self.config.scan_interval_sec
        }


def start_watcher(config: Config):
    """
    启动视频监控器（便捷函数）
    
    Args:
        config: 配置对象
    """
    watcher = VideoWatcher(config)
    try:
        watcher.start()
    finally:
        watcher.stop()


def process_video_file(video_path: str, config: Config) -> bool:
    """
    处理单个视频文件（便捷函数）
    
    Args:
        video_path: 视频文件路径
        config: 配置对象
        
    Returns:
        bool: 处理是否成功
    """
    watcher = VideoWatcher(config)
    try:
        return watcher.process_single_video(video_path)
    finally:
        watcher.stop()
