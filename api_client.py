"""
IOPaint API 客户端模块
封装 LaMa /inpaint HTTP API 调用，支持并发处理
"""
import os
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional
from pathlib import Path
from utils import get_logger


logger = get_logger(__name__)


class IOPaintClient:
    """IOPaint API 客户端"""
    
    def __init__(self, api_url: str, max_workers: int = 3, timeout: int = 30):
        """
        初始化客户端
        
        Args:
            api_url: API 地址
            max_workers: 最大并发数
            timeout: 请求超时时间（秒）
        """
        self.api_url = api_url
        self.max_workers = max_workers
        self.timeout = timeout
        self.session = requests.Session()
        
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'VidCleanser/1.0'
        })
        
        logger.info(f"IOPaint 客户端初始化: {api_url}, 并发数: {max_workers}")
    
    def test_connection(self) -> bool:
        """
        测试 API 连接
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 发送 POST 请求到 inpaint 端点测试连接
            # 不发送文件，只测试端点是否可访问
            response = self.session.post(
                self.api_url,
                timeout=5
            )
            # 400/422 表示端点存在但参数错误，这是正常的
            # 405 表示方法不允许，但端点存在
            return response.status_code in [200, 400, 422, 405]
        except Exception as e:
            logger.warning(f"API 连接测试失败: {e}")
            return False
    
    def repair_frames(self, frames_dir: str, mask_path: str, 
                     output_dir: str) -> bool:
        """
        修复帧序列
        
        Args:
            frames_dir: 输入帧目录
            mask_path: 掩码文件路径
            output_dir: 输出目录
            
        Returns:
            bool: 是否全部成功
        """
        if not os.path.exists(frames_dir):
            logger.error(f"输入帧目录不存在: {frames_dir}")
            return False
        
        if not os.path.exists(mask_path):
            logger.error(f"掩码文件不存在: {mask_path}")
            return False
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取所有帧文件
        frame_files = self._get_frame_files(frames_dir)
        if not frame_files:
            logger.error("没有找到帧文件")
            return False
        
        logger.info(f"开始修复 {len(frame_files)} 帧，使用 {self.max_workers} 个并发")
        
        # 使用线程池并发处理
        success_count = 0
        total_count = len(frame_files)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_frame = {
                executor.submit(
                    self._repair_single_frame, 
                    frame_path, 
                    mask_path, 
                    output_dir
                ): frame_path 
                for frame_path in frame_files
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_frame):
                frame_path = future_to_frame[future]
                try:
                    success = future.result()
                    if success:
                        success_count += 1
                        logger.debug(f"帧修复成功: {os.path.basename(frame_path)}")
                    else:
                        logger.warning(f"帧修复失败: {os.path.basename(frame_path)}")
                except Exception as e:
                    logger.error(f"帧修复异常 {os.path.basename(frame_path)}: {e}")
        
        success_rate = success_count / total_count if total_count > 0 else 0
        logger.info(f"帧修复完成: {success_count}/{total_count} ({success_rate:.1%})")
        
        return success_count == total_count
    
    def _get_frame_files(self, frames_dir: str) -> List[str]:
        """
        获取帧文件列表（按文件名排序）
        
        Args:
            frames_dir: 帧目录
            
        Returns:
            List[str]: 帧文件路径列表
        """
        frame_files = []
        for filename in sorted(os.listdir(frames_dir)):
            if filename.lower().endswith('.png'):
                frame_files.append(os.path.join(frames_dir, filename))
        return frame_files
    
    def _repair_single_frame(self, frame_path: str, mask_path: str, 
                           output_dir: str) -> bool:
        """
        修复单个帧
        
        Args:
            frame_path: 帧文件路径
            mask_path: 掩码文件路径
            output_dir: 输出目录
            
        Returns:
            bool: 是否成功
        """
        try:
            import base64
            
            # 读取图像文件并转换为 base64
            with open(frame_path, 'rb') as frame_file:
                frame_data = frame_file.read()
                frame_base64 = base64.b64encode(frame_data).decode('utf-8')
            
            # 读取掩码文件并转换为 base64
            with open(mask_path, 'rb') as mask_file:
                mask_data = mask_file.read()
                mask_base64 = base64.b64encode(mask_data).decode('utf-8')
            
            # 准备 JSON 请求体
            payload = {
                "image": frame_base64,
                "mask": mask_base64,
                "hd_strategy": "Crop",
                "hd_strategy_crop_trigger_size": 800,
                "hd_strategy_crop_margin": 128,
                "hd_strategy_resize_limit": 1280
            }
            
            # 发送请求
            response = self.session.post(
                self.api_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                # 保存结果
                output_filename = os.path.basename(frame_path)
                output_path = os.path.join(output_dir, output_filename)
                
                # 直接保存二进制响应数据
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                return True
            else:
                logger.warning(f"API 返回错误状态码: {response.status_code}")
                logger.warning(f"错误响应: {response.text[:200]}")
                return False
                    
        except requests.exceptions.Timeout:
            logger.warning(f"请求超时: {os.path.basename(frame_path)}")
            return False
        except requests.exceptions.RequestException as e:
            logger.warning(f"请求异常: {os.path.basename(frame_path)}, {e}")
            return False
        except Exception as e:
            logger.error(f"修复帧异常: {os.path.basename(frame_path)}, {e}")
            return False
    
    def repair_single_frame_with_retry(self, frame_path: str, mask_path: str, 
                                     output_dir: str, max_retries: int = 1) -> bool:
        """
        修复单个帧（带重试）
        
        Args:
            frame_path: 帧文件路径
            mask_path: 掩码文件路径
            output_dir: 输出目录
            max_retries: 最大重试次数
            
        Returns:
            bool: 是否成功
        """
        for attempt in range(max_retries + 1):
            if self._repair_single_frame(frame_path, mask_path, output_dir):
                return True
            
            if attempt < max_retries:
                logger.info(f"重试修复帧: {os.path.basename(frame_path)} (尝试 {attempt + 2})")
                time.sleep(1)  # 重试前等待1秒
        
        return False
    
    def close(self):
        """关闭客户端"""
        self.session.close()
        logger.debug("IOPaint 客户端已关闭")


def create_client(api_url: str, max_workers: int = 3) -> IOPaintClient:
    """
    创建 IOPaint 客户端
    
    Args:
        api_url: API 地址
        max_workers: 最大并发数
        
    Returns:
        IOPaintClient: 客户端实例
    """
    return IOPaintClient(api_url, max_workers)


def test_api_connection(api_url: str) -> bool:
    """
    测试 API 连接
    
    Args:
        api_url: API 地址
        
    Returns:
        bool: 连接是否成功
    """
    client = IOPaintClient(api_url)
    try:
        return client.test_connection()
    finally:
        client.close()
