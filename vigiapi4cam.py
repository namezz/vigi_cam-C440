"""
VIGI攝影機API控制模組

此模組提供與TP-Link VIGI攝影機的API通訊功能，包括：
- 身份驗證與連線管理
- 警報聲音控制
- 音量設定
- 攝影機串流管理

主要功能：
1. 透過HTTPS與攝影機建立安全連線
2. 支援手動觸發聲光警報
3. 可設定不同的警報聲音類型
4. 提供音量控制功能
5. 整合攝影機串流功能

"""
import os
import hashlib  # 用於密碼雜湊處理
import json     # 用於JSON資料格式處理
import base64   # Base64編碼/解碼
from urllib import parse  # URL解析功能
import urllib3  # HTTP客戶端庫

# 導入自定義的攝影機串流模組
from cam_stream import CameraStream

# 加密相關功能
from cryptography.hazmat.primitives.asymmetric import padding  # RSA加密填充
from cryptography.hazmat.primitives import serialization       # 金鑰序列化

# --- 使用者設定區域 ---
IP_ADDRESS = '192.168.0.60'  # 攝影機IP位址
USERNAME = 'admin'           # 登入使用者名稱
PASSWORD = '123456'          # 登入密碼

# --- 腳本設定區域 ---
# CONTROL_PORT = 443         # HTTPS控制埠（已整合到類別中）
# BASE_URL = f"https://{IP_ADDRESS}:{CONTROL_PORT}"  # 基礎URL（已整合到類別中）

# --- 忽略SSL憑證警告 ---
# 由於攝影機使用自簽名憑證，需要忽略SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class VigiApi:
    """
    VIGI攝影機API控制類別
    
    此類別封裝了與TP-Link VIGI攝影機進行API通訊的所有功能，
    包括身份驗證、警報控制、音量設定等。
    
    Attributes:
        ip (str): 攝影機的IP位址
        username (str): 登入使用者名稱
        password (str): 登入密碼
        stok (str): 認證後取得的session token
        base_url (str): API的基礎URL
        headers (dict): HTTP請求標頭
        http (urllib3.PoolManager): HTTP客戶端實例
        _alarm_initialized (bool): 警報設定是否已初始化
    """
    
    def __init__(self, ip, username, password):
        """
        初始化VIGI API實例
        
        Args:
            ip (str): 攝影機IP位址
            username (str): 登入使用者名稱 
            password (str): 登入密碼
        """
        # 基本連線參數
        self.ip = ip
        self.username = username
        self.password = password
        self.stok = None  # 認證token，初始為空
        
        # 建立API連線URL（固定使用443埠）
        self.base_url = f"https://{self.ip}:443"
        
        # 設定HTTP請求標頭
        self.headers = {
            "Accept": "application/json", 
            "Content-Type": "application/json; charset=UTF-8"
        }
        
        # 建立HTTP客戶端實例
        self.http = self._create_http_client()
        
        # 警報初始化狀態標記
        self._alarm_initialized = False

    def _create_http_client(self):
        """
        建立自定義的HTTP客戶端
        
        由於VIGI攝影機使用特定的SSL/TLS設定，需要建立自定義的HTTP客戶端
        來確保連線的相容性和安全性。
        
        Returns:
            urllib3.PoolManager: 配置好的HTTP客戶端實例
        """
        # 建立SSL上下文並設定加密套件
        # 使用AES256-GCM-SHA384加密套件以確保安全性
        context = urllib3.util.create_urllib3_context()
        context.set_ciphers("AES256-GCM-SHA384")
        context.check_hostname = False  # 停用主機名稱檢查（因為使用IP位址）
        
        # 建立並回傳HTTP連線池管理器
        # cert_reqs="CERT_NONE" 表示不驗證SSL憑證（攝影機使用自簽名憑證）
        return urllib3.PoolManager(cert_reqs="CERT_NONE", ssl_context=context)

    def _get_md5_password(self):
        """
        產生密碼的MD5雜湊值
        
        VIGI API需要特定格式的密碼雜湊，必須在密碼前加上固定前綴
        然後計算MD5雜湊值並轉為大寫。
        
        Returns:
            str: 加密後的密碼雜湊值（大寫）
        """
        # VIGI API要求的固定前綴
        prefix = "TPCQ75NF2Y:"
        
        # 組合前綴和原始密碼
        prefixed_password = f"{prefix}{self.password}"
        
        # 計算MD5雜湊值
        md5 = hashlib.md5()
        md5.update(prefixed_password.encode('utf-8'))
        
        # 回傳大寫的十六進位雜湊值
        return md5.hexdigest().upper()

    def authenticate(self):
        """
        執行攝影機身份驗證
        
        VIGI API的身份驗證流程：
        1. 向攝影機請求加密資訊（nonce和公鑰）
        2. 使用RSA公鑰加密密碼和nonce
        3. 發送登入請求並取得session token
        
        Returns:
            bool: 驗證成功回傳True，失敗回傳False
        """
        # print("步驟 1: 正在執行身份驗證...")
        try:
            # === 第一階段：取得加密資訊 ===
            auth_req_body = {
                'user_management': {'get_encrypt_info': None}, 
                'method': 'do'
            }
            
            # 發送請求取得nonce和公鑰
            auth_req = self.http.request(
                "POST", 
                f"{self.base_url}/", 
                headers=self.headers, 
                body=json.dumps(auth_req_body), 
                timeout=5
            )
            
            # 解析回應資料
            auth_data = json.loads(auth_req.data.decode('utf-8'))['data']
            nonce, key = auth_data['nonce'], auth_data['key']
            
            # === 第二階段：準備加密密碼 ===
            # 取得MD5加密的密碼
            password_hash = self._get_md5_password()
            
            # 解碼並載入RSA公鑰
            public_key_der = base64.b64decode(parse.unquote(key))
            public_key = serialization.load_der_public_key(public_key_der)
            
            # 使用RSA公鑰加密密碼+nonce組合
            encrypted = public_key.encrypt(
                f"{password_hash}:{nonce}".encode(), 
                padding.PKCS1v15()
            )
            encrypted_password = base64.b64encode(encrypted).decode()
            
            # === 第三階段：發送登入請求 ===
            login_body = {
                "method": "do", 
                "login": {
                    "username": self.username, 
                    "password": encrypted_password, 
                    "passwdType": "md5",     # 指定密碼類型為MD5
                    "encrypt_type": "2"     # 指定加密類型為RSA
                }
            }
            
            # 發送登入請求
            resp = self.http.request(
                "POST", 
                f"{self.base_url}/", 
                body=json.dumps(login_body), 
                headers=self.headers
            )
            
            # 解析登入回應
            resp_data = json.loads(resp.data.decode('utf-8'))
            
            # 檢查登入結果
            if resp_data.get("error_code") == 0 and resp_data.get("stok"):
                # 驗證成功，儲存session token
                self.stok = resp_data["stok"]
                print(f"  - 驗證成功！取得權杖: {self.stok}\n")
                return True
            else:
                # 驗證失敗
                print(f"  - 錯誤：驗證失敗，錯誤碼: {resp_data.get('error_code')}")
                return False
                
        except Exception as e:
            print(f"身份驗證過程中發生錯誤: {e}")
            return False

    def _send_request(self, payload):
        """
        發送API請求的通用方法
        
        此方法處理所有需要認證的API請求，會自動加上session token
        並處理錯誤情況。
        
        Args:
            payload (dict): 要發送的API請求資料
            
        Returns:
            dict: API回應資料，若發生錯誤則回傳None
        """
        # 檢查是否已通過身份驗證
        if not self.stok:
            print("錯誤: 請先執行 authenticate()")
            return None
            
        # 建立包含session token的完整URL
        url = f"{self.base_url}/stok={self.stok}/ds"
        
        # 輸出除錯資訊（可選）
        print(f"  - Payload: {json.dumps(payload)}")
        
        try:
            # 發送POST請求
            response = self.http.request(
                "POST", 
                url, 
                headers=self.headers, 
                body=json.dumps(payload), 
                timeout=5
            )
            
            # 解析回應資料
            response_data = json.loads(response.data.decode('utf-8'))
            
            # 輸出回應資訊（可選）
            print(f"  - 攝影機回應: {response_data}")
            
            return response_data
            
        except Exception as e:
            print(f"  - 請求時發生錯誤: {e}")
            return None

    def _initialize_alarm_settings(self):
        """
        初始化警報基礎設定
        
        在使用警報功能前，需要先初始化攝影機的警報相關設定，
        包括關閉預設的聲音和燈光警報，並設定揚聲器基本參數。
        
        Returns:
            bool: 初始化成功回傳True，失敗回傳False
        """
        print("  - 正在初始化警報基礎設定...")
        
        # 設定警報基礎參數
        payload = {
            "msg_alarm": {
                "chn1_msg_alarm_info": {
                    "sound_alarm_enabled": "off",  # 關閉自動聲音警報
                    "light_alarm_enabled": "off",  # 關閉自動燈光警報
                    "alarm_type": "1"              # 設定預設警報類型
                }
            },
            "audio_config": {
                "speaker": {
                    "mute": "off",          # 確保揚聲器未靜音
                    "system_volume": "10"   # 設定預設音量
                }
            },
            "method": "set"
        }
        
        # 發送設定請求
        response = self._send_request(payload)
        
        # 檢查設定結果
        if response and str(response.get("error_code")) == "0":
            self._alarm_initialized = True
            print("  - 警報基礎設定初始化成功。\n")
            return True
        else:
            print("  - 警報基礎設定初始化失敗。\n")
            return False

    def set_volume(self, volume: int):
        """
        設定攝影機揚聲器音量
        
        調整攝影機內建揚聲器的音量大小，範圍為0-100。
        
        Args:
            volume (int): 音量大小，範圍0-100
                         0 = 最小音量
                         100 = 最大音量
                         
        Returns:
            bool: 設定成功回傳True，失敗回傳False
        """
        # 驗證音量範圍
        if not 0 <= volume <= 100:
            print("錯誤: 音量必須在 0 到 100 之間。")
            return False
            
        print(f"正在設定音量為: {volume}...")
        
        # 建立音量設定請求
        payload = {
            "audio_config": {
                "speaker": {
                    "system_volume": str(volume)  # API要求字串格式
                }
            }, 
            "method": "set"
        }
        
        # 發送設定請求
        response = self._send_request(payload)
        
        # 檢查設定結果
        if response and str(response.get("error_code")) == "0":
            print(f"  - 成功設定音量為 {volume}。\n")
            return True
        else:
            print(f"  - 設定音量失敗。")
            return False

    def set_alarm_sound_type(self, sound_id: int):
        """
        設定警報聲音類型
        
        更改警報觸發時播放的聲音類型。不同的sound_id對應不同的內建聲音。
        
        Args:
            sound_id (int): 聲音類型ID
                           常見值：
                           0 = 警報聲
                           1 = 鈴聲
                           2-9 = 其他內建聲音（依攝影機型號而異）
                           
        Returns:
            bool: 設定成功回傳True，失敗回傳False
        """
        print(f"正在設定警報聲音類型為: {sound_id}...")
        
        # 建立聲音類型設定請求
        payload = {
            "msg_alarm": {
                "chn1_msg_alarm_info": {
                    "alarm_type": str(sound_id)  # API要求字串格式
                }
            }, 
            "method": "set"
        }
        
        # 發送設定請求
        response = self._send_request(payload)
        
        # 檢查設定結果
        if response and str(response.get("error_code")) == "0":
            print(f"  - 成功設定聲音類型為 {sound_id}。\n")
            return True
        else:
            print(f"  - 設定聲音類型失敗。")
            return False

    def trigger_manual_alarm(self, action: str, sound_id: int = 1, volume: int = 30):
        """
        (尚未解決控制燈光的問題，只控制聲音)
        手動觸發或停止聲光警報
        
        此方法可以立即觸發或停止攝影機的聲光警報功能。
        在觸發警報前會自動設定音量和聲音類型。
        
        Args:
            action (str): 警報動作
                         "start" = 開始警報
                         "stop" = 停止警報
            sound_id (int, optional): 警報聲音ID，預設為1（鈴聲）
                                    0 = 警報聲
                                    1 = 鈴聲  
                                    2-9 = 其他聲音
            volume (int, optional): 音量大小，預設為30，範圍0-100
            
        Returns:
            bool: 操作成功回傳True，失敗回傳False
        """
        # 判斷動作類型並準備顯示文字
        action_text = "觸發" if action == "start" else "停止"
        print(f"正在手動{action_text}聲光警報...")
        
        # 如果警報設定未初始化，先進行初始化
        if not self._alarm_initialized:
            if not self._initialize_alarm_settings():
                return False

        # 如果是開始警報，先設定音量和聲音類型
        if action == "start":
            self.set_volume(volume)
            self.set_alarm_sound_type(sound_id)
        
        # 建立手動警報觸發請求
        payload = {
            "msg_alarm": {
                "manual_msg_alarm": {
                    "action": action  # "start" 或 "stop"
                }
            }, 
            "method": "do"
        }
        
        # 發送警報控制請求
        response = self._send_request(payload)
        
        # 檢查操作結果
        if response and str(response.get("error_code")) == "0":
            print(f"  - 成功{action_text}聲光警報！\n")
            return True
        else:
            print(f"  - {action_text}聲光警報失敗。")
            return False

    def test_audio_alarm(self, sound_id=1):
        """
        執行聲音警報測試
        
        觸發一次性的聲音測試，用於測試特定聲音ID的播放效果。
        此功能只播放聲音，不會觸發燈光警報。
        
        Args:
            sound_id (int, optional): 要測試的聲音ID，預設為1
                                    0 = 警報聲
                                    1 = 鈴聲
                                    2-9 = 其他聲音（依攝影機型號而異）
                                    
        Returns:
            bool: 測試指令發送成功回傳True，失敗回傳False
            
        Note:
            此方法只發送測試指令，不會等待播放完成。
            聲音會在攝影機端自動播放一次。
        """
        print("正在發送聲音測試指令...")
        
        # 建立聲音測試請求
        payload = {
            "usr_def_audio_alarm": {
                "test_audio": {
                    "id": sound_id  # 指定要測試的聲音ID
                }
            },
            "method": "do"
        }
        
        # 發送測試請求
        response = self._send_request(payload)
        
        # 檢查測試結果
        if response and str(response.get("error_code")) == "0":
            print("  - 成功發送聲音測試指令。\n")
            return True
        else:
            print("  - 發送聲音測試指令失敗。")
            return False

    def create_camera_stream(self, port: int = 554, stream_path: str = 'stream1') -> CameraStream:
        """
        建立攝影機視訊串流實例
        
        建立一個CameraStream物件，用於處理攝影機的RTSP視訊串流。
        此方法會使用當前的連線資訊來建立串流連線。
        
        Args:
            port (int, optional): RTSP串流埠號，預設為554
                                 VIGI攝影機通常使用554埠提供RTSP服務
            stream_path (str, optional): 串流路徑，預設為'stream1'
                                       常見值：
                                       'stream1' = 主串流（高解析度）
                                       'stream2' = 次串流（低解析度）
                                       
        Returns:
            CameraStream: 配置好的攝影機串流實例
            
        Example:
            >>> api = VigiApi('192.168.1.100', 'admin', 'password')
            >>> api.authenticate()
            >>> stream = api.create_camera_stream()
            >>> stream.start()  # 開始串流
        """
        return CameraStream(
            ip=self.ip,              # 攝影機IP位址
            port=port,               # RTSP埠號
            user=self.username,      # 登入使用者名稱
            pwd=self.password,       # 登入密碼
            stream_path=stream_path  # 串流路徑
        )
    
    def get_custom_audio_list(self):
        """
        獲取攝影機上已存在的自訂聲音列表。
        """
        print("步驟 2: 正在獲取自訂聲音列表...")
        payload = {"usr_def_audio_alarm": {"table": ["usr_def_audio"]}, "method": "get"}
        response = self._send_request(payload)
        
        if not response or str(response.get("error_code")) != "0":
            print(f"  - 錯誤：從攝影機獲取資料失敗或收到錯誤碼。\n    - 回應: {response}")
            return []

        try:
            # 根據您提供的回應，我們直接從根部開始解析
            raw_audio_list = response.get("usr_def_audio_alarm", {}).get("usr_def_audio", [])
            
            if not raw_audio_list:
                print("  - 解析結果：攝影機上目前沒有自訂聲音。\n")
                return []

            # --- 這是處理動態鍵名 ("file_1", "file_2") 的核心邏輯 ---
            processed_list = []
            for item_wrapper in raw_audio_list:
                # item_wrapper 的形式是 {"file_X": {...}}
                # 我們只需要裡面的值，不需要鍵名
                if isinstance(item_wrapper, dict) and item_wrapper:
                    # 取得字典中的第一個值，這就是我們需要的聲音資訊物件
                    audio_info = next(iter(item_wrapper.values()))
                    
                    # 解碼 URL 編碼的名稱 (例如 'custom%20audio%201' -> 'custom audio 1')
                    if 'name' in audio_info:
                        audio_info['name'] = parse.unquote(audio_info['name'])
                        
                    processed_list.append(audio_info)
            # --- 核心邏輯結束 ---
            
            print("  - 解析成功，當前自訂聲音列表:")
            for item in processed_list:
                print(f"    - ID: {item.get('id')}, 名稱: '{item.get('name')}'")
            print("")
            
            return processed_list
            
        except Exception as e:
            print(f"  - 錯誤：解析 JSON 回應時發生嚴重錯誤: {e}")
            return []

    def upload_custom_audio(self, file_path: str, sound_id: int, sound_name: str = None):
        """
        上傳自訂聲音檔案並指派給指定的聲音ID。
        
        Args:
            file_path (str): g711a 音檔的完整路徑。
            sound_id (int): 要建立或覆蓋的目標聲音 ID (例如 101, 102, 103)。
            sound_name (str, optional): 要為此聲音設定的名稱。如果為 None，則使用檔案名稱。
            
        Returns:
            bool: 操作成功回傳 True，失敗回傳 False。
        """
        if not self.stok:
            print("錯誤: 請先執行 authenticate()")
            return False

        if not os.path.exists(file_path):
            print(f"錯誤: 找不到檔案 '{file_path}'")
            return False

        file_name_only = os.path.basename(file_path)
        if sound_name is None:
            sound_name = os.path.splitext(file_name_only)[0]

        # --- 第一步: 將檔案上傳到臨時位置 ---
        upload_url = f"{self.base_url}/stok={self.stok}/admin/system/upload_usr_def_audio"
        print(f"步驟 3: [上傳階段] 正在上傳 '{file_name_only}'...")
        
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()

            encoded_body, content_type = urllib3.encode_multipart_formdata({
                'filename': (file_name_only, file_data, 'application/octet-stream')
            })
            
            upload_headers = self.headers.copy()
            upload_headers['Content-Type'] = content_type

            response = self.http.request("POST", upload_url, headers=upload_headers, body=encoded_body, timeout=15)
            upload_response_data = json.loads(response.data.decode('utf-8'))
            print(f"  - 上傳回應: {upload_response_data}")

            if str(upload_response_data.get("error_code")) != "0":
                print(f"  - 錯誤：檔案上傳階段失敗，錯誤碼: {upload_response_data.get('error_code')}")
                return False
                
        except Exception as e:
            print(f"  - 錯誤：檔案上傳過程中發生錯誤: {e}")
            return False

        # --- 第二步: 確認上傳，將臨時檔案指派給指定的ID和名稱 ---
        print(f"步驟 4: [確認階段] 正在將上傳的檔案指派給 ID {sound_id}，並命名為 '{sound_name}'...")
        confirm_payload = {
            "system": {
                "upload_usr_def_audio": {
                    "id": sound_id,
                    "name": sound_name
                }
            },
            "method": "do"
        }
        
        # 注意：這個請求是發送到通用的 /ds 端點
        confirm_response = self._send_request(confirm_payload)
        
        if confirm_response and str(confirm_response.get("error_code")) == "0":
            print(f"  - 成功建立/覆蓋 ID {sound_id} 的音檔。\n")
            return True
        else:
            print(f"  - 錯誤：確認/指派階段失敗。\n")
            return False

    def sync_custom_audios(self, audio_files: list):
        """
        同步自訂音檔，檢查並填滿 101、102、103 槽位。

        Args:
            audio_files (list): 一個包含音檔路徑的列表。
                                列表的順序對應想要上傳到的槽位順序。
                                例如：[path1, path2, path3] 
                                path1 -> ID 101, path2 -> ID 102, path3 -> ID 103

        Returns:
            bool: 所有需要的操作都成功完成回傳 True，否則回傳 False。
        """
        if not self.stok:
            print("錯誤: 請先成功執行 authenticate()")
            return False

        print("=== 開始同步自訂音檔流程 ===")
        
        # 1. 獲取當前攝影機上的自訂聲音列表
        current_audios = self.get_custom_audio_list()
        if current_audios is None: # 檢查是否獲取失敗
            return False
            
        existing_ids = {item.get('id') for item in current_audios}
        print(f"目前已存在的聲音 ID: {existing_ids if existing_ids else '無'}")
        
        # 2. 遍歷目標槽位 (101, 102, 103) 和對應的檔案
        # zip 會將兩個列表配對，例如 (101, path1), (102, path2), ...
        target_slots = range(101, 101 + len(audio_files))
        
        all_successful = True
        for sound_id, file_path in zip(target_slots, audio_files):
            # 檢查目前槽位是否已經有聲音
            if sound_id in existing_ids:
                print(f"ID {sound_id} 已存在，跳過上傳。")
                continue

            # 如果槽位是空的，就上傳對應的檔案
            print(f"\n發現槽位 ID {sound_id} 為空，準備上傳 '{os.path.basename(file_path)}'...")
            
            # 使用我們已經寫好的上傳函式
            success = self.upload_custom_audio(
                file_path=file_path,
                sound_id=sound_id,
                # 自動使用檔案名稱（不含副檔名）作為聲音名稱
                sound_name=os.path.splitext(os.path.basename(file_path))[0] 
            )
            
            if not success:
                print(f"!! 上傳到 ID {sound_id} 失敗，終止同步流程。!!")
                all_successful = False
                break # 如果有一次上傳失敗，就停止後續操作

        if all_successful:
            print("\n=== 自訂音檔同步完成！ ===")
        
        return all_successful
    
    def delete_custom_audio(self, sound_ids_to_delete: list):
        """
        刪除攝影機上一個或多個指定的自訂聲音。
        
        Args:
            sound_ids_to_delete (list): 一個包含要刪除的聲音ID的列表。
                                      例如: [101] 或 [101, 103]
                                      
        Returns:
            bool: 刪除指令發送成功且攝影機回應無誤則回傳 True，否則回傳 False。
        """
        if not self.stok:
            print("錯誤: 請先成功執行 authenticate()")
            return False

        if not sound_ids_to_delete:
            print("提示: 未提供任何要刪除的聲音ID，操作已取消。")
            return True

        print(f"步驟: 正在請求刪除聲音 ID: {sound_ids_to_delete}...")
        
        # 根據分析，建立刪除請求的 payload
        payload = {
            "usr_def_audio_alarm": {
                "delete_audio": {
                    "id": sound_ids_to_delete
                }
            },
            "method": "do"
        }
        
        # 發送請求
        response = self._send_request(payload)
        
        # 檢查回應
        if response and str(response.get("error_code")) == "0":
            print(f"  - 成功發送刪除指令。\n")
            return True
        else:
            print(f"  - 錯誤：刪除操作失敗。")
            if response:
                print(f"    - 攝影機回應: {response}")
            return False
        
    def rename_custom_audio(self, sound_id: int, new_name: str):
        """
        修改指定ID的自訂聲音的名稱
        
        此方法用於變更已上傳到攝影機的自訂聲音檔案名稱。
        只會修改顯示名稱，不會影響實際的音檔內容。
        
        Args:
            sound_id (int): 要修改名稱的聲音 ID (例如: 101, 102, 103)
            new_name (str): 要設定的新名稱 (不可為空字串)
            
        Returns:
            bool: 操作成功回傳 True，失敗回傳 False
            
        Example:
            >>> api.rename_custom_audio(101, "警報聲音1")
            >>> # 將ID 101的聲音重新命名為"警報聲音1"
        """
        # 檢查是否已完成身份驗證
        if not self.stok:
            print("錯誤: 請先成功執行 authenticate()")
            return False

        # 驗證新名稱不可為空
        if not new_name:
            print("錯誤: 新名稱不可為空。")
            return False

        print(f"步驟: 正在請求將 ID {sound_id} 的名稱修改為 '{new_name}'...")
        
        # 建立API請求的資料結構
        # 注意：API要求 id 和 name 參數都必須是陣列格式，即使只有一個值
        payload = {
            "usr_def_audio_alarm": {           # 自訂音訊警報功能模組
                "modify_audio": {              # 修改音訊子功能
                    "id": [sound_id],          # 要修改的聲音ID陣列
                    "name": [new_name]         # 對應的新名稱陣列
                }
            },
            "method": "do"                     # 指定這是執行動作的請求
        }
        
        # 發送修改名稱的請求到攝影機
        response = self._send_request(payload)
        
        # 解析攝影機的回應結果
        if response and str(response.get("error_code")) == "0":
            # error_code 為 "0" 表示操作成功
            print(f"  - 成功將 ID {sound_id} 的名稱修改為 '{new_name}'。\n")
            return True
        else:
            # 任何非 "0" 的 error_code 都表示操作失敗
            print(f"  - 錯誤：修改名稱操作失敗。")
            if response:
                print(f"    - 攝影機回應: {response}")
            return False
