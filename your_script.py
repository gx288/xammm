import time
import csv
import logging
import os
import sys
import json
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from seleniumbase import SB  # Import SeleniumBase thay vì uc

# Lấy đường dẫn đúng cho file khi chạy dưới dạng thực thi hoặc mã nguồn
def get_resource_path(relative_path):
    """Lấy đường dẫn đúng cho file khi chạy dưới dạng thực thi hoặc mã nguồn"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(os.path.dirname(sys.executable), relative_path)
    else:
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

def login_to_website(sb, username, password):
    """Hàm thực hiện đăng nhập vào website dùng SeleniumBase"""
    logging.info("Đang thực hiện đăng nhập...")
    try:
        username_field = WebDriverWait(sb.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "login"))
        )
        username_field.send_keys(username)
        time.sleep(random.uniform(1, 3))
        logging.info("Đã nhập tên đăng nhập")
        password_field = sb.driver.find_element(By.NAME, "password")
        password_field.send_keys(password)
        time.sleep(random.uniform(1, 3))
        logging.info("Đã nhập mật khẩu")
        login_button = sb.driver.find_element(By.XPATH, "//button[contains(., 'Đăng nhập')]")
        login_button.click()
        time.sleep(random.uniform(2, 5))
        logging.info("Đã click nút đăng nhập")
        WebDriverWait(sb.driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.fr-element.fr-view[contenteditable='true']"))
        )
        logging.info("Đăng nhập thành công và đã chuyển đến trang bình luận")
        return True
    except (TimeoutException, NoSuchElementException) as e:
        logging.error(f"Lỗi trong quá trình đăng nhập: {str(e)}")
        logging.info(f"Current URL: {sb.driver.current_url}")
        with open('error_page_source.html', 'w', encoding='utf-8') as f:
            f.write(sb.driver.page_source)
        sb.driver.save_screenshot('login_error.png')
        logging.info("Đã lưu page source và screenshot để debug")
        return False

def post_comment(sb, comment_text):
    """Hàm thực hiện đăng bình luận dùng SeleniumBase"""
    logging.info(f"Đang đăng bình luận: {comment_text}")
    try:
        editor = WebDriverWait(sb.driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.fr-element.fr-view[contenteditable='true']"))
        )
        sb.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", editor)
        time.sleep(random.uniform(1, 3))
        sb.driver.execute_script("arguments[0].innerHTML = '';", editor)
        sb.driver.execute_script("arguments[0].innerText = arguments[1];", editor, comment_text)
        sb.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", editor)
        time.sleep(random.uniform(1, 3))
        logging.info("Đã nhập nội dung bình luận")
        submit_button = WebDriverWait(sb.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@type='submit' and .//span[contains(text(), 'Trả lời')]]"))
        )
        sb.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
        sb.driver.execute_script("arguments[0].click();", submit_button)
        time.sleep(random.uniform(2, 5))
        logging.info("Đã click nút đăng bình luận")
        WebDriverWait(sb.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.fr-element.fr-view[contenteditable='true']"))
        )
        logging.info("Bình luận đã được đăng thành công!")
        time.sleep(1)
        return True
    except (TimeoutException, NoSuchElementException, ElementClickInterceptedException) as e:
        logging.error(f"Lỗi trong quá trình đăng bình luận: {str(e)}")
        logging.info(f"Current URL: {sb.driver.current_url}")
        with open('error_page_source.html', 'w', encoding='utf-8') as f:
            f.write(sb.driver.page_source)
        sb.driver.save_screenshot('post_error.png')
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
                return
    except FileNotFoundError:
        logging.error(f"File data.csv không tồn tại tại {csv_path}")
        return
    except Exception as e:
        logging.error(f"Lỗi khi đọc file CSV: {str(e)}")
        return
    
    with SB(uc=True, headless=True, cdp_mode=True) as sb:  # UC mode + CDP để bypass Cloudflare
        try:
            logging.info(f"Đang mở trang web: {website_url}")
            # Dùng uc_open_with_reconnect để retry nếu Cloudflare challenge
            sb.uc_open_with_reconnect(website_url, reconnect_time=10)  # Retry 10s nếu fail
            time.sleep(random.uniform(10, 20))  # Wait cho challenge resolve
            
            # Check nếu vẫn Cloudflare
            if "Just a moment..." in sb.get_current_title() or "Just a moment..." in sb.get_page_source():
                logging.error("Vẫn phát hiện Cloudflare anti-bot page")
                with open('cloudflare_page_source.html', 'w', encoding='utf-8') as f:
                    f.write(sb.get_page_source())
                sb.driver.save_screenshot('cloudflare_error.png')
                logging.info("Đã lưu page source và screenshot để debug")
                # Thử activate CDP mode lại để bypass
                sb.activate_cdp_mode(website_url)
                sb.uc_open_with_reconnect(website_url, reconnect_time=15)
                time.sleep(15)
            
            WebDriverWait(sb.driver, 30).until(  # Tăng timeout
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            logging.info("Trang web đã tải xong (bypass Cloudflare thành công)")
            
            username = os.getenv('USERNAME')
            password = os.getenv('PASSWORD')
            if not username or not password:
                logging.error("USERNAME hoặc PASSWORD không được cung cấp qua environment variables")
                return
            
            if not login_to_website(sb, username, password):
                logging.error("Đăng nhập thất bại, dừng chương trình")
                return
            
            logging.info("Đang xử lý bình luận...")
            if post_comment(sb, comment):
                logging.info("Đăng bình luận thành công, xóa bình luận khỏi file data.csv")
                remove_first_comment_from_csv(csv_path)
            else:
                logging.error("Không thể đăng bình luận, giữ nguyên file data.csv")
        except Exception as e:
            logging.error(f"Lỗi không mong muốn: {str(e)}")
            with open('error_page_source.html', 'w', encoding='utf-8') as f:
                f.write(sb.get_page_source())
            sb.driver.save_screenshot('error_page.png')
            logging.info("Đã lưu page source và screenshot để debug")

if __name__ == "__main__":
    main()
