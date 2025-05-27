# 導入所需的套件
import requests
import certifi
import os
import webbrowser
import traceback
import pytesseract
from PIL import Image
import io
import base64
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import time
from datetime import datetime
import numpy as np
import cv2
from multiprocessing import Process, Queue

def preprocess_image_cv(img: Image.Image) -> Image.Image:
    """優化的圖像前處理函數"""
    img_np = np.array(img.convert("L"))  # 灰階
    blur = cv2.GaussianBlur(img_np, (3, 3), 0)
    _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = np.ones((2, 2), np.uint8)
    clean = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    return Image.fromarray(clean)

def ocr_with_timeout(image: Image.Image, queue: Queue):
    """帶有超時控制的 OCR 處理"""
    try:
        text = pytesseract.image_to_string(
            image,
            config='--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        )
        queue.put(text)
    except Exception as e:
        queue.put("")

def safe_ocr(image: Image.Image, timeout=5) -> str:
    """安全的 OCR 函數，帶有超時保護"""
    queue = Queue()
    p = Process(target=ocr_with_timeout, args=(image, queue))
    p.start()
    p.join(timeout)
    if p.is_alive():
        p.terminate()
        print("⚠️ OCR 超時，終止子程序")
        return ""
    return queue.get() if not queue.empty() else ""

# 設定登入資訊
login_url = "https://sys.ndhu.edu.tw/gc/sportcenter/SportsFields/login.aspx"  # 登入網址
account = "411122051"    # 帳號
password = "2003.11.05"  # 密碼

# 設定Chrome瀏覽器選項
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--start-maximized")           # 最大化視窗
chrome_options.add_experimental_option("detach", True)     # 保持瀏覽器開啟
chrome_options.add_argument("--disable-popup-blocking")    # 禁用彈出視窗阻擋

# 啟動瀏覽器
driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 20)  # 設定等待時間最多20秒

try:
    # 1. 登入流程
    driver.get(login_url)     # 開啟登入頁面
    time.sleep(5)            # 等待頁面載入
    
    # 輸入帳號密碼
    account_input = driver.find_element(By.ID, "MainContent_TxtUSERNO")
    password_input = driver.find_element(By.ID, "MainContent_TxtPWD")
    account_input.clear()
    password_input.clear()
    account_input.send_keys(account)
    password_input.send_keys(password)
    
    # 點擊登入按鈕
    login_button = wait.until(EC.element_to_be_clickable((By.ID, "MainContent_Button1")))
    login_button.click()
    time.sleep(5)
    
    # 2. 點擊進入預約頁面
    button2 = wait.until(EC.element_to_be_clickable((By.ID, "MainContent_Button2")))
    button2.click()
    time.sleep(3)
    
    # 3. 設定預約日期
    try:
        target_date = "2025/06/02"  # 設定目標日期
        
        # 使用JavaScript設定日期
        js_code = f"""
            document.getElementById('MainContent_TextBox1').value = '{target_date}';
            __doPostBack('ctl00$MainContent$TextBox1','');
        """
        driver.execute_script(js_code)
        time.sleep(3)
        
        # 點擊查詢按鈕
        query_button = wait.until(EC.element_to_be_clickable((By.ID, "MainContent_Button1")))
        driver.execute_script("arguments[0].click();", query_button)
        time.sleep(3)
        
    except Exception as e:
        print(f"設定日期時出錯: {e}")
        print(traceback.format_exc())
    
    # 4. 選擇場地
    try:
        court_select = driver.find_element(By.ID, "MainContent_DropDownList1")
        select = Select(court_select)
        
        # 選擇特定場地 
        court_value = "VOL0A"
        select.select_by_value(court_value)
        # 籃球場選項:
        # BSK0A: 籃球場A
        # BSK0B: 籃球場B
        # BSK0C: 籃球場C
        # BSK0D: 籃球場D
        # BSK0E: 籃球場E
        # BSK0F: 籃球場F
        # BSK0G: 籃球場I (K書中心)
        # BSK0H: 籃球場J (k書中心)
        # BSK0J: 籃球場L (集賢館場地)
        # BSK0K: 籃球場K (集賢館場地)
        # BSKR1: 籃球場G (原R1)
        # BSKR2: 籃球場H (原R2)
        
        # 排球場選項:
        # VOL0A: 排球場A-女
        # VOL0B: 排球場B-男
        # VOL0C: 排球場C-女
        # VOL0D: 排球場D-男
        # VOL0E: 排球場E-女
        # VOL0F: 排球場F-男
        # VOL0G: 排球場G-女
        # VOL0H: 排球場H-男
        # VOL0J: 排球場L-女 (集賢館場地)
        # VOL0K: 排球場K-男 (集賢館場地)
        # VOLR1: 排球場I-女 (原R1)
        # VOLR2: 排球場J-男 (原R2)
        
        # 操場選項:
        # ARO0A: 柔道教室A
        # GYM0A: 韻律教室
        # PLA0A: 體育室前廣場
        # TRK0A: 田徑場
        
        # 體育館選項:
        # XDNCE: 壽豐館-舞蹈教室
        # XGMB1: 壽館場B-羽1
        # XGMB2: 壽館場B-羽2
        # XGMB3: 壽館場B-羽3
        # XGMB4: 壽館場B-羽4
        # XGMC1: 壽館場C-排1
        # XGMC2: 壽館場C-排2
        # XGMC3: 壽館場C-排3
        # XGMC4: 壽館場C-排4
        # XGYMA: 壽館場A-籃球
        # XTKDO: 壽豐館-跆拳道教室
        # XTT0W: 壽豐體育館桌球室全部
        
        # 網球場選項:
        # TNS0G: 網球場G
        # TNS0H: 網球場H
        # XTNA1: 網球場1
        # XTNA2: 網球場2
        # XTNB1: 網球場3
        # XTNB2: 網球場4
        # XTNB3: 網球場5
        # XTNB4: 網球場6 (紅土)
        # XTNB5: 網球場7 (紅土)
        time.sleep(1)
        # 觸發場地選擇的更新
        driver.execute_script("__doPostBack('ctl00$MainContent$DropDownList1','')")
        time.sleep(2)
        
    except Exception as e:
        print(f"選擇場地時出錯: {e}")
        print(traceback.format_exc())
    
    # 5. 選擇時段
    try:
        time.sleep(2)
        
        # 定義預約時段
        desired_time = "06~08"
        
        # 修改後的XPath，更精確地定位按鈕
        time_slot_xpath = f"""
            //tr[
                td[contains(text(), '06')] and 
                td/button[contains(@type, 'button') and 
                contains(., '[申請]') and 
                contains(., '{desired_time}')]
            ]//button
        """
        
        # 等待按鈕出現並點擊
        time_slot_button = wait.until(
            EC.presence_of_element_located((By.XPATH, time_slot_xpath))
        )
        
        # 使用JavaScript點擊按鈕
        driver.execute_script("arguments[0].scrollIntoView(true);", time_slot_button)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", time_slot_button)
        time.sleep(2)

    except Exception as e:
        print(f"選擇時段時出錯: {e}")
        print(traceback.format_exc())
        
    # 6. 處理驗證碼
    try:
        attempt_count = 0
        success_count = 0
        failure_count = 0
        max_retries = 5

        while attempt_count < max_retries:
            try:
                attempt_count += 1
                print(f"\n--- 第 {attempt_count} 次嘗試 ---")
                time.sleep(2)

                wait_long = WebDriverWait(driver, 15)

                # 取得驗證碼圖片
                try:
                    captcha_img = wait_long.until(
                        EC.presence_of_element_located((By.ID, "MainContent_imgCaptcha"))
                    )
                    img_base64 = driver.execute_script("""
                        var img = document.getElementById('MainContent_imgCaptcha');
                        var canvas = document.createElement('canvas');
                        canvas.width = img.width;
                        canvas.height = img.height;
                        var ctx = canvas.getContext('2d');
                        ctx.drawImage(img, 0, 0);
                        return canvas.toDataURL('image/png').split(',')[1];
                    """)
                except:
                    print("⚠️ 等待驗證碼圖片超時，嘗試換一張...")
                    try:
                        # 使用 JavaScript 找到並點擊換圖按鈕
                        driver.execute_script("""
                            var btn = document.querySelector('button[onclick="refreshCaptcha()"]');
                            if(btn) btn.click();
                        """)
                        print("✅ 已點擊換圖按鈕")
                        time.sleep(2)
                    except Exception as e:
                        print(f"❌ 換圖失敗，嘗試重新整理頁面: {e}")
                        driver.refresh()
                        time.sleep(3)
                    continue

                # 圖片處理和 OCR
                img_data = base64.b64decode(img_base64)
                img = Image.open(io.BytesIO(img_data))
                processed_img = preprocess_image_cv(img)
                
                # 使用安全的 OCR
                captcha_text = safe_ocr(processed_img, timeout=5)
                captcha_text = re.sub(r'[^A-Za-z0-9]', '', captcha_text).strip()
                print(f"辨識出的驗證碼：{captcha_text}")

                if len(captcha_text) != 5:
                    print("⚠️ 驗證碼格式錯誤，重新產生")
                    refresh_button = driver.find_element(
                        By.XPATH, "//button[@onclick='refreshCaptcha()']"
                    )
                    refresh_button.click()
                    time.sleep(2)
                    continue

                # 輸入驗證碼
                captcha_input = wait_long.until(
                    EC.presence_of_element_located((By.ID, "MainContent_txtCaptcha"))
                )
                captcha_input.clear()
                captcha_input.send_keys(captcha_text)
                time.sleep(1)

                # 送出驗證
                confirm_button = wait_long.until(
                    EC.element_to_be_clickable((By.ID, "MainContent_Button3"))
                )
                confirm_button.click()
                time.sleep(2)

                # 驗證結果檢查
                try:
                    wait_long.until(
                        EC.presence_of_element_located((By.ID, "MainContent_imgCaptcha"))
                    )
                    failure_count += 1
                    print("❌ 驗證失敗")
                    print(f"🔄 統計：成功 {success_count} 次，失敗 {failure_count} 次")
                    driver.find_element(
                        By.XPATH, "//button[@onclick='refreshCaptcha()']"
                    ).click()
                    time.sleep(2)
                    continue
                except:
                    success_count += 1
                    print("✅ 驗證碼輸入成功！")
                    print(f"📊 最終統計：總嘗試 {attempt_count} 次，成功率 {(success_count/attempt_count)*100:.1f}%")
                    break

            except Exception as e:
                print(f"❌ 處理驗證碼時出錯: {e}")
                print(traceback.format_exc())
                if attempt_count >= max_retries:
                    print("達到最大重試次數，程式終止")
                    break
                driver.refresh()
                time.sleep(3)

        print("🎯 驗證碼處理結束")

    except Exception as e:
        print(f"驗證碼模組發生錯誤: {e}")
        print(traceback.format_exc())

finally:
    pass  # 保持瀏覽器開啟