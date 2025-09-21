# VidCleanser

批量去除视频水印工具，基于 IOPaint/LaMa 的 HTTP API 实现自动化的视频水印去除。

## 功能特性

- 🔍 **自动监控**：监控输入目录，发现新的 .mp4 文件自动入队处理
- 🎯 **智能检测**：自动检测视频左上角和右下角的水印位置
- ⚡ **高效处理**：视频级串行处理，帧级并行修复
- 🛡️ **稳定可靠**：失败自动清理，不保留中间文件
- 📝 **详细日志**：完整的处理日志和状态监控

## 项目结构

```
VidCleanser/
├── main.py                 # 程序入口
├── watcher.py              # 目录轮询与任务队列
├── processor.py            # 单视频处理管线
├── mask.py                 # 角落检测与掩码生成
├── api_client.py           # IOPaint API 调用封装
├── ffmpeg_utils.py         # FFmpeg 工具封装
├── config.py               # 配置管理
├── utils.py                # 公共工具函数
├── requirements.txt        # 依赖包
├── config.yaml             # 配置文件
└── README.md               # 使用说明
```

## 安装依赖

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 2. 安装 FFmpeg

**Windows:**
1. 下载 FFmpeg: https://ffmpeg.org/download.html
2. 解压到任意目录（如 `C:\ffmpeg`）
3. 将 `C:\ffmpeg\bin` 添加到系统 PATH 环境变量

**验证安装:**
```bash
ffmpeg -version
ffprobe -version
```

### 3. 启动 IOPaint 服务

```bash
iopaint start --model lama --device cuda --port 8080
```

## 配置说明

编辑 `config.yaml` 文件：

```yaml
# 输入目录（递归扫描 .mp4 文件）
input_dir: "E:/videos_in"

# 输出目录（清理后的视频保存位置）
output_dir: "E:/videos_out"

# 临时工作目录（处理过程中的临时文件）
temp_dir: "E:/videos_temp"

# IOPaint LaMa API 地址
lama_api_url: "http://127.0.0.1:8080/inpaint"

# 帧级 LaMa 并行数（建议 2-4）
api_workers: 3

# 角落检测的抽样帧数
sample_frames: 10

# 掩码宽度比例（相对视频宽度）
mask_ratio_w: 0.20

# 掩码高度比例（相对视频高度）
mask_ratio_h: 0.10

# 角落检测模式：lt(左上), rb(右下), lt_rb(两角)
corners_mode: "lt_rb"

# 轮询扫描间隔（秒）
scan_interval_sec: 10

# 日志级别：debug/info/warn/error
log_level: "info"
```

## 使用方法

### 1. 监控模式（推荐）

自动监控输入目录，发现新视频自动处理：

```bash
python main.py
```

### 2. 处理单个视频

```bash
python main.py --video "path/to/video.mp4"
```

### 3. 验证环境

```bash
python main.py --validate
```

### 4. 查看状态

```bash
python main.py --status
```

### 5. 使用自定义配置

```bash
python main.py --config "my_config.yaml"
```

## 处理流程

1. **监控扫描**：每 10 秒扫描一次输入目录
2. **视频入队**：发现新的 .mp4 文件自动加入处理队列
3. **串行处理**：严格按顺序处理，一次只处理一个视频
4. **角落检测**：抽样 10 帧检测左上/右下角水印位置
5. **掩码生成**：根据检测结果生成修复掩码
6. **帧提取**：将视频拆分为帧序列
7. **并行修复**：使用 LaMa API 并行修复所有帧
8. **视频合成**：将修复后的帧合成为新视频
9. **清理完成**：删除原视频和中间文件，保留清理后的视频

## 处理策略

- **视频级串行**：确保系统稳定性，避免资源冲突
- **帧级并行**：提高处理效率，充分利用 API 并发能力
- **失败清理**：处理失败时自动清理工作目录，保留原视频
- **无断点续跑**：失败后重新开始，确保处理完整性

## 日志文件

程序运行日志保存在 `logs/app.log`，包含：
- 处理开始/结束时间
- 检测到的水印位置
- 处理帧数和耗时
- 成功/失败状态
- 错误详情

## 注意事项

1. **确保 IOPaint 服务运行**：程序启动前必须先启动 IOPaint 服务
2. **FFmpeg 可用性**：确保 FFmpeg 和 FFprobe 在系统 PATH 中
3. **磁盘空间**：处理过程中需要足够的临时空间存储帧文件
4. **网络连接**：确保能够访问 IOPaint API 服务
5. **文件权限**：确保对输入/输出目录有读写权限

## 故障排除

### 1. FFmpeg 不可用
```
错误: FFmpeg 或 FFprobe 不可用
解决: 安装 FFmpeg 并添加到 PATH 环境变量
```

### 2. API 连接失败
```
错误: 无法连接到 IOPaint API
解决: 确保 IOPaint 服务已启动，检查端口和地址配置
```

### 3. 视频处理失败
```
错误: 视频处理失败
解决: 检查视频文件是否损坏，查看详细日志了解具体错误
```

### 4. 权限问题
```
错误: 无法创建输出目录
解决: 检查目录权限，确保程序有写入权限
```

## 性能优化

1. **调整并发数**：根据系统性能调整 `api_workers` 参数
2. **优化抽样帧数**：减少 `sample_frames` 可提高检测速度
3. **调整扫描间隔**：根据视频产生频率调整 `scan_interval_sec`
4. **使用 SSD**：将临时文件存储在 SSD 上可显著提高处理速度

## 技术栈

- **Python 3.8+**
- **OpenCV**: 图像处理和角落检测
- **NumPy**: 数值计算
- **Requests**: HTTP API 调用
- **FFmpeg**: 视频处理
- **IOPaint/LaMa**: AI 图像修复

## 许可证

本项目仅供学习和研究使用。
