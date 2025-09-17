import time
import csv
import logging
import os
import sys
import json
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager  # Giữ nguyên, nhưng uc sẽ tự quản lý driver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc  # Thêm import này

# Lấy đường dẫn đúng cho file khi chạy dưới dạng thực thi hoặc mã nguồn
def get_resource_path(relative_path):
    """Lấy đường dẫn đúng cho file khi chạy dưới dạng thực thi hoặc mã nguồn"""
    if hasattr(sys, '_MEIPASS'):
        # Khi chạy dưới dạng file thực thi, lấy đường dẫn từ thư mục chứa .exe
        return os.path.join(os.path.dirname(sys.executable), relative_path)
    else:
        # Khi chạy mã nguồn, lấy đường dẫn tương đối
        return os.path.join(os.path.dirname(__file__), relative_path)

# Đọc cấu hình từ file config.json
def load_config():
    """Đọc đường dẫn file data.csv và URL website từ config.json"""
    config_path = get_resource_path('config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config = json.load(file)
            website_url = config.get('website_url', 'https://xamvn.blog/threads/171635/reply')
            data_csv_path = config.get('data_csv_path', 'data.csv')
            return {'website_url': website_url, 'data_csv_path': data_csv_path}
    except FileNotFoundError:
        logging.error(f"File config.json không tồn tại tại {config_path}")
        return {'website_url': 'https://xamvn.blog/threads/171635/reply', 'data_csv_path': 'data.csv'}
    except json.JSONDecodeError:
        logging.error("File config.json không đúng định dạng JSON")
        return {'website_url': 'https://xamvn.blog/threads/171635/reply', 'data_csv_path': 'data.csv'}

# Thiết lập logging với encoding UTF-8
log_directory = os.path.join(os.path.expanduser("~"), "Documents")
if not os.path.exists(log_directory):
    os.makedirs(log_directory)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_directory, "selenium_automation.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Đảm bảo console hỗ trợ UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def setup_driver():
    """Khởi tạo WebDriver với undetected_chromedriver để tránh phát hiện bot."""
    logging.info("Đang khởi tạo undetected-chromedriver...")
    options = Options()
    options.add_argument('--headless')  # Giữ headless, nhưng uc sẽ làm nó giống thật hơn
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-plugins-discovery')
    options.add_argument('--disable-dev-tools')
    options.add_argument('--window-size=1920,1080')
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Sử dụng undetected_chromedriver thay vì webdriver.Chrome
    driver = uc.Chrome(options=options)  # uc tự download và patch driver
    
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.execute_cdp_cmd('Emulation.setLocaleOverride', {"locale": "vi-VN"})
    driver.execute_cdp_cmd('Emulation.setTimezoneOverride', {"timezoneId": "Asia/Ho_Chi_Minh"})
    
    return driver

def login_to_website(driver, username, password):
    """Hàm thực hiện đăng nhập vào website"""
    logging.info("Đang thực hiện đăng nhập...")
    try:
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "login"))
        )
        username_field.send_keys(username)
        time.sleep(random.uniform(1, 3))
        logging.info("Đã nhập tên đăng nhập")
        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys(password)
        time.sleep(random.uniform(1, 3))
        logging.info("Đã nhập mật khẩu")
        login_button = driver.find_element(By.XPATH, "//button[contains(., 'Đăng nhập')]")
        login_button.click()
        time.sleep(random.uniform(2, 5))
        logging.info("Đã click nút đăng nhập")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.fr-element.fr-view[contenteditable='true']"))
        )
        logging.info("Đăng nhập thành công và đã chuyển đến trang bình luận")
        return True
    except (TimeoutException, NoSuchElementException) as e:
        logging.error(f"Lỗi trong quá trình đăng nhập: {str(e)}")
        logging.info(f"Current URL: {driver.current_url}")
        with open('error_page_source.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        driver.save_screenshot('login_error.png')
        logging.info("Đã lưu page source và screenshot để debug")
        return False

def post_comment(driver, comment_text):
    """Hàm thực hiện đăng bình luận"""
    logging.info(f"Đang đăng bình luận: {comment_text}")
    try:
        editor = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.fr-element.fr-view[contenteditable='true']"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", editor)
        time.sleep(random.uniform(1, 3))
        driver.execute_script("arguments[0].innerHTML = '';", editor)
        driver.execute_script("arguments[0].innerText = arguments[1];", editor, comment_text)
        driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", editor)
        time.sleep(random.uniform(1, 3))
        logging.info("Đã nhập nội dung bình luận")
        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@type='submit' and .//span[contains(text(), 'Trả lời')]]"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
        driver.execute_script("arguments[0].click();", submit_button)
        time.sleep(random.uniform(2, 5))
        logging.info("Đã click nút đăng bình luận")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.fr-element.fr-view[contenteditable='true']"))
        )
        logging.info("Bình luận đã được đăng thành công!")
        time.sleep(1)
        return True
    except (TimeoutException, NoSuchElementException, ElementClickInterceptedException) as e:
        logging.error(f"Lỗi trong quá trình đăng bình luận: {str(e)}")
        logging.info(f"Current URL: {driver.current_url}")
        with open('error_page_source.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        driver.save_screenshot('post_error.png')
        logging.info("Đã lưu page source và screenshot để debug")
        return False

def remove_first_comment_from_csv(csv_path):
    """Xóa bình luận đầu tiên từ file data.csv và lưu lại các bình luận còn lại"""
    try:
        comments = []
        with open(csv_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            comments = [row[0].strip() for row in csv_reader if row and row[0].strip()]
        if not comments:
            logging.info("File data.csv đã trống, không còn bình luận để xóa.")
            return
        with open(csv_path, 'w', encoding='utf-8', newline='') as file:
            csv_writer = csv.writer(file)
            for comment in comments[1:]:
                csv_writer.writerow([comment])
        logging.info("Đã xóa bình luận đầu tiên khỏi file data.csv")
    except Exception as e:
        logging.error(f"Lỗi khi xóa bình luận khỏi file data.csv: {str(e)}")

def main():
    driver = setup_driver()
    config = load_config()
    website_url = config['website_url']
    csv_path = get_resource_path(config['data_csv_path'])
    comment = None
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            comments = [row[0].strip() for row in csv_reader if row and row[0].strip()]
            if comments:
                comment = comments[0]
                logging.info(f"Đã đọc bình luận đầu tiên: {comment}")
            else:
                logging.error("File data.csv trống hoặc không có bình luận hợp lệ")
                driver.quit()
                return
    except FileNotFoundError:
        logging.error(f"File data.csv không tồn tại tại {csv_path}")
        driver.quit()
        return
    except Exception as e:
        logging.error(f"Lỗi khi đọc file CSV: {str(e)}")
        driver.quit()
        return
    try:
        logging.info(f"Đang mở trang web: {website_url}")
        driver.get(website_url)
        time.sleep(random.uniform(10, 15))  # Chờ lâu hơn để Cloudflare challenge tự giải quyết
        if "Just a moment..." in driver.title or "Just a moment..." in driver.page_source:
            logging.error("Vẫn phát hiện Cloudflare anti-bot page")
            with open('cloudflare_page_source.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            driver.save_screenshot('cloudflare_error.png')
            logging.info("Đã lưu page source và screenshot để debug")
            driver.quit()
            return
        WebDriverWait(driver, 20).until(  # Tăng timeout
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        logging.info("Trang web đã tải xong")
        username = os.getenv('USERNAME')
        password = os.getenv('PASSWORD')
        if not username or not password:
            logging.error("USERNAME hoặc PASSWORD không được cung cấp qua environment variables")
            driver.quit()
            return
        if not login_to_website(driver, username, password):
            logging.error("Đăng nhập thất bại, dừng chương trình")
            return
        logging.info("Đang xử lý bình luận...")
        if post_comment(driver, comment):
            logging.info("Đăng bình luận thành công, xóa bình luận khỏi file data.csv")
            remove_first_comment_from_csv(csv_path)
        else:
            logging.error("Không thể đăng bình luận, giữ nguyên file data.csv")
    except Exception as e:
        logging.error(f"Lỗi không mong muốn: {str(e)}")
    finally:
        driver.quit()
        logging.info("Đã đóng trình duyệt")

if __name__ == "__main__":
    main()
