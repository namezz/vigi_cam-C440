from vigiapi4cam import *
import time
import threading


if __name__ == "__main__":
    # 手動警報持續時間 (秒)
    ALARM_DURATION = 5 

    # ip, username, password
    vigi_cam = VigiApi(IP_ADDRESS, USERNAME, PASSWORD)
    
    if vigi_cam.authenticate():
        print("選擇功能：")
        print("1. 觸發手動聲光警報 (可選聲音/音量)")
        print("2. 測試喇叭聲音 (僅播放聲音)")
        print("3. 開啟攝影機串流")
        print("4. 同時觸發警報和串流")
        
        choice = input("請輸入選項 (1-4): ").strip()
        
        if choice == "1":
            print("\n--- 觸發手動聲光警報 ---")
            sound_id_str = input("請輸入要觸發的聲音 ID (例如 1 或 2，預設為 1): ").strip()
            volume_str = input("請輸入音量 (0-100，預設為 30): ").strip()
            
            sound_id = int(sound_id_str) if sound_id_str.isdigit() else 1
            volume = int(volume_str) if volume_str.isdigit() else 30

            if vigi_cam.trigger_manual_alarm(action="start", sound_id=sound_id, volume=volume):
                print(f"警報已觸發，將在 {ALARM_DURATION} 秒後自動停止...")
                time.sleep(ALARM_DURATION)
                vigi_cam.trigger_manual_alarm(action="stop")
            
        elif choice == "2":
            print("\n--- 測試喇叭聲音 ---")
            sound_id_str = input("請輸入要測試的聲音 ID (例如 0 或 1，預設為 1): ").strip()
            sound_id = int(sound_id_str) if sound_id_str.isdigit() else 1
            vigi_cam.test_audio_alarm(sound_id=101)

        elif choice == "3":
            print("\n--- 開啟攝影機串流 ---")
            camera_stream = vigi_cam.create_camera_stream()
            print("串流視窗已開啟，在視窗上按 'q' 鍵退出串流...")
            try:
                camera_stream.show_live_stream('VIGI Camera Live Stream')
            except Exception as e:
                print(f"顯示串流時發生錯誤: {e}")
            
        elif choice == "4":
            print("\n--- 同時觸發警報和串流 ---")
            camera_stream = vigi_cam.create_camera_stream()
            
            stream_thread_obj = threading.Thread(
                target=camera_stream.show_live_stream, 
                args=('VIGI Camera Live Stream',)
            )
            stream_thread_obj.daemon = True
            stream_thread_obj.start()
            
            print("串流已在背景執行，2秒後觸發警報...")
            time.sleep(2)
            
            if vigi_cam.trigger_manual_alarm(action="start", sound_id=1, volume=10):
                time.sleep(ALARM_DURATION)
                vigi_cam.trigger_manual_alarm(action="stop")
            
            print("\n警報演示完畢。串流仍在執行。")
            input("按 Enter 鍵停止串流並結束程式...")
            camera_stream.release()
            time.sleep(1)
            
        else:
            print("無效的選項")
    else:
        print("驗證失敗，無法繼續操作。")