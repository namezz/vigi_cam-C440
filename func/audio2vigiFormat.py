import subprocess
import os
import datetime

def convert_to_g711(input_file, filename='output.g711', max_size=128*1024):
    # 以目前這個 .py 檔案所在的目錄為基準
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, 'audio', 'g711')
    os.makedirs(output_dir, exist_ok=True)

    # 取得原始檔名（不含副檔名）
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    # 取得當前時間字串
    time_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    # 新檔名
    filename = f"{base_name}_{time_str}.g711"
    output_path = os.path.join(output_dir, filename)

    try:
        # 先計算最大時長（秒）以確保檔案大小不超過 128KB
        # G.711 A-law: 8000 Hz * 1 byte per sample = 8000 bytes/sec
        max_duration = max_size / 8000
        
        # 使用 ffmpeg 轉檔，加入時長限制和更詳細的參數
        cmd = [
            'ffmpeg', '-i', input_file,
            '-t', str(max_duration),  # 限制時長
            '-acodec', 'pcm_alaw',    # G.711 A-law 編碼
            '-ar', '8000',            # 取樣率 8kHz
            '-ac', '1',               # 單聲道
            '-f', 'alaw',             # 輸出格式為 A-law
            '-y', output_path         # 覆寫輸出檔案
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
    except FileNotFoundError:
        raise RuntimeError("ffmpeg is not installed or not found in system PATH. Please install ffmpeg and try again.")
    except subprocess.CalledProcessError as e:
        # 輸出更詳細的錯誤資訊
        error_msg = f"ffmpeg failed with error code {e.returncode}\n"
        if e.stderr:
            error_msg += f"Error output: {e.stderr}\n"
        if e.stdout:
            error_msg += f"Standard output: {e.stdout}"
        raise RuntimeError(error_msg)

    # 確認檔案大小並截斷（如果需要）
    if os.path.exists(output_path):
        file_size = os.path.getsize(output_path)
        if file_size > max_size:
            with open(output_path, 'rb+') as f:
                f.truncate(max_size)
            print(f"警告: 檔案已截斷至 {max_size} bytes")
        
        print(f"轉檔成功，檔案大小: {os.path.getsize(output_path)} bytes")
    else:
        raise RuntimeError("轉檔後檔案不存在")

    return output_path

if __name__ == "__main__":
    # 替換為您的輸入檔案路徑
    input_file = "yourpath\\to\\your\\audiofile.g711"  # 這裡請填入您要轉檔的音檔路徑
    try:
        output_file = convert_to_g711(input_file)
        print(f"轉檔完成，輸出檔案位於: {output_file}")
    except Exception as e:
        print(f"轉檔失敗: {e}")
