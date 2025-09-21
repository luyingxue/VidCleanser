"""
VidCleanser 主程序入口
批量去除视频水印的监控程序
"""
import sys
import argparse
import signal
from pathlib import Path

from config import load_config
from utils import setup_logging, get_logger
from processor import validate_environment
from watcher import start_watcher, process_video_file


def signal_handler(signum, frame):
    """信号处理器"""
    logger = get_logger(__name__)
    logger.info(f"收到信号 {signum}，正在退出...")
    sys.exit(0)


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="VidCleanser - 批量去除视频水印")
    parser.add_argument(
        "--config", 
        default="config.yaml",
        help="配置文件路径 (默认: config.yaml)"
    )
    parser.add_argument(
        "--video",
        help="处理单个视频文件（不启动监控模式）"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="验证环境配置后退出"
    )
    parser.add_argument(
        "--status",
        action="store_true", 
        help="显示当前状态"
    )
    
    args = parser.parse_args()
    
    try:
        # 加载配置
        config = load_config(args.config)
        
        # 设置日志
        setup_logging(config.log_level)
        logger = get_logger(__name__)
        
        logger.info("VidCleanser 启动")
        logger.info(f"配置: {config.input_dir} -> {config.output_dir}")
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 验证环境
        if args.validate:
            logger.info("验证环境配置...")
            is_valid, message = validate_environment(config)
            if is_valid:
                logger.info("✓ " + message)
                print("环境验证通过")
                return 0
            else:
                logger.error("✗ " + message)
                print(f"环境验证失败: {message}")
                return 1
        
        # 处理单个视频
        if args.video:
            if not Path(args.video).exists():
                logger.error(f"视频文件不存在: {args.video}")
                print(f"错误: 视频文件不存在: {args.video}")
                return 1
            
            logger.info(f"处理单个视频: {args.video}")
            success = process_video_file(args.video, config)
            
            if success:
                logger.info("视频处理成功")
                print("视频处理成功")
                return 0
            else:
                logger.error("视频处理失败")
                print("视频处理失败")
                return 1
        
        # 显示状态
        if args.status:
            from watcher import VideoWatcher
            watcher = VideoWatcher(config)
            try:
                status = watcher.get_status()
                print(f"监控状态: {'运行中' if status['running'] else '已停止'}")
                print(f"输入目录: {status['input_dir']}")
                print(f"输出目录: {status['output_dir']}")
                print(f"总视频数: {status['total_videos']}")
                print(f"有效视频数: {status['valid_videos']}")
                print(f"处理中视频数: {status['processing_videos']}")
                print(f"扫描间隔: {status['scan_interval']}秒")
            finally:
                watcher.stop()
            return 0
        
        # 启动监控模式
        logger.info("启动监控模式")
        print("VidCleanser 监控模式启动")
        print(f"监控目录: {config.input_dir}")
        print(f"输出目录: {config.output_dir}")
        print(f"扫描间隔: {config.scan_interval_sec}秒")
        print("按 Ctrl+C 停止监控")
        print("-" * 50)
        
        # 验证环境
        is_valid, message = validate_environment(config)
        if not is_valid:
            logger.error(f"环境验证失败: {message}")
            print(f"错误: {message}")
            return 1
        
        # 开始监控
        start_watcher(config)
        
        logger.info("VidCleanser 正常退出")
        return 0
        
    except KeyboardInterrupt:
        logger.info("用户中断程序")
        print("\n程序被用户中断")
        return 0
    except Exception as e:
        logger.error(f"程序异常: {e}")
        print(f"程序异常: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
