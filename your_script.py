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
from seleniumbase import SB

def get_resource_path(relative_path):
    """Lấy đường dẫn đúng cho file khi chạy dưới dạng thực thi hoặc mã nguồn"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(os.path.dirname(sys.executable), relative_path)
    else:
        return os.path.join(os.path.dirname(__file__), relative_path)

def load_config():
    """Đọc đường dẫn file data.csv và URL website từ config.json"""
    config_path = get_resource_path('config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config = json.load(file)
            website_url = config.get('website_url', 'https://xamvn.guru/threads/171635/reply')
            data_csv_path = config.get('data_csv_path', 'data.csv')
            return {'website_url': website_url, 'data_csv_path': data_csv_path}
    except FileNotFoundError:
        logging.error(f"File config.json không tồn tại tại {config_path}")
        return {'website_url': 'https://xamvn.guru/threads/171635/reply', 'data_csv_path': 'data.csv'}
    except json.JSONDecodeError:
        logging.error("File config.json không đúng định dạng JSON")
        return {'website_url': 'https://xamvn.guru/threads/171635/reply', 'data_csv_path': 'data.csv'}

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

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def login_to_website(sb, username, password):
    """Hàm thực hiện đăng nhập trên trang login (nếu đã ở trang login)"""
    logging.info("Đang thực hiện đăng nhập...")
    try:
        # Đợi trường username có thể nhập
        username_field = WebDriverWait(sb.driver, 15).until(
            EC.element_to_be_clickable((By.NAME, "login"))
        )
        username_field.clear()
        username_field.send_keys(username)
        sb.sleep(random.uniform(1, 3))
        logging.info("Đã nhập tên đăng nhập")

        password_field = sb.driver.find_element(By.NAME, "password")
        password_field.clear()
        password_field.send_keys(password)
        sb.sleep(random.uniform(1, 3))
        logging.info("Đã nhập mật khẩu")

        # Check "Duy trì trạng thái đăng nhập"
        try:
            remember_checkbox = sb.driver.find_element(By.NAME, "remember")
            if not remember_checkbox.is_selected():
                sb.execute_script("arguments[0].click();", remember_checkbox)
        except NoSuchElementException:
            pass

        # Tìm nút Đăng nhập bằng text
        login_button = WebDriverWait(sb.driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(@class, 'button--primary') and .//span[text()='Đăng nhập']]"))
        )
        sb.execute_script("arguments[0].scrollIntoView({block: 'center'});", login_button)
        sb.sleep(1)

        # Thử click bình thường, nếu lỗi thì dùng JS
        try:
            login_button.click()
            logging.info("Đã click nút đăng nhập (thông thường)")
        except ElementClickInterceptedException:
            logging.warning("Click bị chặn, dùng JavaScript...")
            sb.execute_script("arguments[0].click();", login_button)
            logging.info("Đã click nút đăng nhập (JS)")

        sb.sleep(random.uniform(4, 7))

        # Đợi chuyển sang trang reply (editor hiện ra)
        WebDriverWait(sb.driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.fr-element.fr-view[contenteditable='true']"))
        )
        logging.info("Đăng nhập thành công và đã chuyển đến trang bình luận")
        return True

    except Exception as e:
        logging.error(f"Lỗi trong quá trình đăng nhập: {str(e)}")
        logging.info(f"Current URL: {sb.get_current_url()}")
        with open('error_page_source.html', 'w', encoding='utf-8') as f:
            f.write(sb.get_page_source())
        sb.save_screenshot('login_error.png')
        return False

def post_comment(sb, comment_text):
    """Hàm thực hiện đăng bình luận dùng SeleniumBase"""
    logging.info(f"Đang đăng bình luận: {comment_text}")
    try:
        editor = WebDriverWait(sb.driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.fr-element.fr-view[contenteditable='true']"))
        )
        # Nội dung bạn muốn thêm
        contact_info = "Thanks"
        final_text = f"{comment_text}\n{contact_info}"
        
        sb.execute_script("arguments[0].scrollIntoView({block: 'center'});", editor)
        sb.sleep(random.uniform(1, 3))
        sb.execute_script("arguments[0].innerHTML = '';", editor)
        
        # Sử dụng final_text đã có dòng liên hệ
        sb.execute_script("arguments[0].innerText = arguments[1];", editor, final_text)
        
        sb.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", editor)
        sb.sleep(random.uniform(1, 3))
        logging.info("Đã nhập nội dung bình luận có kèm thông tin liên hệ")
        # Simulate human: Random scroll
        sb.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
        sb.sleep(random.uniform(1, 2))
        
        submit_button = WebDriverWait(sb.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@type='submit' and .//span[contains(text(), 'Trả lời')]]"))
        )
        sb.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
        sb.execute_script("arguments[0].click();", submit_button)
        sb.sleep(random.uniform(3, 6))
        logging.info("Đã click nút đăng bình luận")
        
        # Wait cho editor reset sau post
        WebDriverWait(sb.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.fr-element.fr-view[contenteditable='true']"))
        )
        logging.info("Bình luận đã được đăng thành công!")
        sb.sleep(2)
        return True
    except (TimeoutException, NoSuchElementException, ElementClickInterceptedException) as e:
        logging.error(f"Lỗi trong quá trình đăng bình luận: {str(e)}")
        logging.info(f"Current URL: {sb.get_current_url()}")
        with open('error_page_source.html', 'w', encoding='utf-8') as f:
            f.write(sb.get_page_source())
        sb.save_screenshot('post_error.png')
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
    
    with SB(uc=True, headless=True) as sb:
        try:
            logging.info(f"Đang mở trang web: {website_url}")
            # Retry tối đa 3 lần để bypass Cloudflare (nếu còn)
            max_retries = 3
            for attempt in range(max_retries):
                sb.uc_open_with_reconnect(website_url, reconnect_time=20)
                sb.sleep(random.uniform(15, 25))  # Dùng sb.sleep thay time.sleep
                
                # Fix: Sử dụng sb.get_title() và sb.get_page_source()
                if "Just a moment..." not in sb.get_title() and "Just a moment..." not in sb.get_page_source():
                    break  # Thành công, thoát vòng retry
                logging.warning(f"Cloudflare anti-bot page detected (attempt {attempt + 1}/{max_retries})")
                with open(f'cloudflare_page_source_attempt_{attempt + 1}.html', 'w', encoding='utf-8') as f:
                    f.write(sb.get_page_source())
                sb.save_screenshot(f'cloudflare_error_attempt_{attempt + 1}.png')
                logging.info(f"Đã lưu page source và screenshot (attempt {attempt + 1}) để debug")
                if attempt < max_retries - 1:
                    sb.sleep(random.uniform(5, 10))
            
            if "Just a moment..." in sb.get_title() or "Just a moment..." in sb.get_page_source():
                logging.error("Không thể bypass Cloudflare sau tất cả các lần thử")
                return
            
            WebDriverWait(sb.driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            logging.info("Trang web đã tải xong (bypass Cloudflare thành công)")
            
            username = os.getenv('USERNAME')
            password = os.getenv('PASSWORD')
            if not username or not password:
                logging.error("USERNAME hoặc PASSWORD không được cung cấp qua environment variables")
                return
            
            # Thực hiện login (sẽ tự động nếu ở trang login)
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
            sb.save_screenshot('error_page.png')
            logging.info("Đã lưu page source và screenshot để debug")

if __name__ == "__main__":
    main()
