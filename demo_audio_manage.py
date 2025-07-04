from vigiapi4cam import *
from audio2vigiFormat import convert_to_g711

if __name__ == "__main__":

    # 替換為您的輸入檔案路徑
    input_file = r'yourpath\to\your\audiofile.g711'  # 這裡請填入您要轉檔的音檔路徑
    try:
        output_file = convert_to_g711(input_file)
        print(f"轉檔完成，輸出檔案位於: {output_file}")
    except Exception as e:
        print(f"轉檔失敗: {e}")

    
    # --- 設定您要依序上傳的音檔 ---
    # 將您的音檔路徑按順序放入這個列表中
    # 程式會嘗試將第一個檔案上傳到 ID 101，第二個到 102，以此類推
    # 最多處理前三個檔案
    AUDIO_FILES_TO_SYNC = [
        r"yourpath\XDD.g711", # 這個會被上傳到 ID 101 (如果 101 為空)
        rf"{output_file}",    # 這個會被上傳到 ID 102 (如果 102 為空)
        r"yourpath\XDD.g711"  # 這個會被上傳到 ID 103 (如果 103 為空)
    ]

    # --- 程式開始執行 ---
    vigi_cam = VigiApi(IP_ADDRESS, USERNAME, PASSWORD)
    if vigi_cam.authenticate():
        
        # 執行同步函式
        vigi_cam.sync_custom_audios(AUDIO_FILES_TO_SYNC)

        # 同步完成後，再次獲取列表，檢查最終結果
        print("\n最終攝影機上的自訂聲音列表：")
        vigi_cam.get_custom_audio_list()

        # 將您想刪除的聲音 ID 放入這個列表中
        IDS_TO_DELETE = [103] 
        # 2. 執行刪除操作
        if vigi_cam.delete_custom_audio(IDS_TO_DELETE):
            print(f"=== 已成功發送刪除 ID {IDS_TO_DELETE} 的請求 ===")
        else:
            print(f"=== 刪除 ID {IDS_TO_DELETE} 的請求失敗 ===")
        
        # 3. 刪除後，再次獲取列表，確認是否已刪除
        print("\n刪除後，當前自訂聲音列表：")
        vigi_cam.get_custom_audio_list()

        # --- 設定您要修改的目標 ---
        TARGET_ID_TO_RENAME = 101       # 您想修改哪個 ID 的名稱
        NEW_NAME_FOR_AUDIO = "XDD" # 您想給它取的新名字
    
        # 1. 修改前，先看看攝影機上原來的名稱
        print("修改前，當前自訂聲音列表：")
        vigi_cam.get_custom_audio_list()
        
        # 2. 執行修改名稱操作
        if vigi_cam.rename_custom_audio(TARGET_ID_TO_RENAME, NEW_NAME_FOR_AUDIO):
            print(f"=== 已成功發送修改 ID {TARGET_ID_TO_RENAME} 名稱的請求 ===")
        else:
            print(f"=== 修改 ID {TARGET_ID_TO_RENAME} 名稱的請求失敗 ===")
        
        # 3. 修改後，再次獲取列表，確認名稱是否已更新
        print("\n修改後，當前自訂聲音列表：")
        vigi_cam.get_custom_audio_list()