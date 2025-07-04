import cv2
from typing import Optional, Tuple

class CameraStream:
    """攝影機串流類別"""
    
    def __init__(self, ip: str, port: int = 554, user: str = 'admin', 
                 pwd: str = '123456', stream_path: str = 'stream1'):
        """
        初始化攝影機串流
        
        Args:
            ip: 攝影機 IP 位址
            port: RTSP 連接埠 (預設: 554)
            user: 使用者帳號
            pwd: 密碼
            stream_path: 串流路徑
        """
        self.ip = ip
        self.port = port
        self.user = user
        self.pwd = pwd
        self.stream_path = stream_path
        self.rtsp_url = f'rtsp://{user}:{pwd}@{ip}:{port}/{stream_path}'
        self.cap: Optional[cv2.VideoCapture] = None
    
    def connect(self) -> bool:
        """連接攝影機"""
        try:
            self.cap = cv2.VideoCapture(self.rtsp_url)
            if self.cap.isOpened():
                print(f"成功連接到攝影機: {self.ip}")
                return True
            else:
                print(f"無法連接到攝影機: {self.ip}")
                return False
        except Exception as e:
            print(f"連接錯誤: {e}")
            return False
    
    def read_frame(self) -> Tuple[bool, Optional[any]]:
        """讀取一幀畫面"""
        if self.cap is None:
            return False, None
        return self.cap.read()
    
    def show_live_stream(self, window_name: str = 'Camera Live Stream'):
        """顯示即時串流畫面"""
        if not self.connect():
            return
        
        try:
            while True:
                ret, frame = self.read_frame()
                if not ret:
                    print("無法取得畫面")
                    break
                
                cv2.imshow(window_name, frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        finally:
            self.release()
    
    def release(self):
        """釋放資源"""
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        print("攝影機連接已關閉")


if __name__ == "__main__":
    # 使用您原本的設定
    camera = CameraStream(
        ip='192.168.0.11',
        port=554,
        user='admin',
        pwd='123456'
    )
    camera.show_live_stream('VIGI C440 Live')

