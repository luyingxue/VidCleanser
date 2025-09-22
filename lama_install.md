# install.md

## 1. 安装 Python 3.11

1. 打开官方页面下载 **Python 3.11.9 (Windows x86-64 installer)**：  
   👉 [Python 3.11.9 下载地址 (64-bit)](https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe)

2. 运行安装程序时注意选项：  
   - **勾选** ✅ *Add Python 3.11 to PATH*  
   - 点击 *Customize installation* → 保持默认即可  
   - 点击 *Install for all users*（推荐）  
   - 安装完成后，重启 PowerShell，运行验证：  
     ```powershell
     py -3.11 --version
     ```
     预期输出：
     ```
     Python 3.11.9
     ```

---

## 2. 创建工程目录与虚拟环境

在 **E 盘**建立工作目录：

```powershell
mkdir E:\lama -Force
cd E:\lama

:: 创建虚拟环境
py -3.11 -m venv .venv

:: 激活虚拟环境
.\.venv\Scripts\Activate.ps1
```

如果激活报错，执行一次：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

然后重新运行 `.\.venv\Scripts\Activate.ps1`。

---

## 3. 升级基础工具

```powershell
python -m pip install -U pip wheel setuptools
```

---

## 4. 安装 IOPaint (LaMa 封装)

```powershell
pip install -U iopaint
```

---

## 5. 安装 GPU 版 PyTorch

默认安装的 PyTorch 可能是 CPU 版，需要手动换成 CUDA 版。

1. 卸载 CPU 版（如果存在）：
   ```powershell
   python -m pip uninstall -y torch torchvision torchaudio
   ```

2. 安装 CUDA 12.1 版（适配 RTX 40 系列，兼容 CUDA 12.x 驱动）：
   ```powershell
   python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```

---

## 6. 验证 PyTorch 是否能用 GPU

```powershell
python -c "import torch, sys; print(sys.executable); print('torch:', torch.__version__, 'cuda?', torch.cuda.is_available()); print('device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu only')"
```

预期输出（示例）：
```
E:\lama\.venv\Scripts\python.exe
torch: 2.5.1+cu121 cuda? True
device: NVIDIA GeForce RTX 4070
```

---

## 7. 启动 IOPaint (LaMa) 服务

在虚拟环境里运行：

```powershell
iopaint start --model lama --device cuda --port 8080
```

看到日志里包含：
```
Using device: cuda
Running on http://127.0.0.1:8080
```
说明已经成功在 GPU 上运行。

---

## 8. 验证 GPU 是否真的在工作  

### 方法 A：nvidia-smi
在另一个终端运行：
```powershell
nvidia-smi -l 1
```
- 会每秒刷新一次 GPU 状态。  
- 当在 WebUI 点击 **Inpaint** 时，`GPU-Util` 数值会瞬间升高（比如 30%~80%），表示推理正在 GPU 上运行。  

### 方法 B：Windows 任务管理器
1. 打开 **任务管理器** → 切换到 **性能** → **GPU**。  
2. 选择 **GPU → 3D** 图表。  
3. 在 WebUI 上传一张图片并点击 **Inpaint**：  
   - **3D 曲线** 会出现瞬时峰值。  
   - **显存使用**（右侧显存占用条）会显示模型加载占用（通常 1GB~4GB）。  
4. 如果看到曲线有跳动，说明 GPU 正在参与推理。  

---

## 9. 测试 WebUI

1. 打开浏览器访问：  
   👉 <http://127.0.0.1:8080>

2. 上传一张图片，在水印位置用画笔涂抹 → 点击 **Inpaint**。  

3. 观察输出结果是否自然补全。

---

## 10. 测试 HTTP API

准备两张同尺寸图片：  
- `test.png`（原始图片）  
- `mask.png`（白色区域 = 需要去除的水印，黑色区域 = 保留）  

运行：

```powershell
curl -X POST "http://127.0.0.1:8080/inpaint" ^
  -F "image=@test.png" ^
  -F "mask=@mask.png" ^
  -o "out.png"
```

执行完成后会在当前目录生成 `out.png`，水印位置被自动修复。

---

## ✅ 总结

到这里你就完成了从零到跑通 LaMa 的完整流程：  
- 安装 Python 3.11  
- 建立虚拟环境  
- 安装 IOPaint  
- 配置 GPU 版 PyTorch  
- 启动 LaMa 服务  
- 验证 GPU（nvidia-smi / Windows 任务管理器）  
- 测试 WebUI 和 API  
