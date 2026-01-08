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
    """Đọc danh sách các task từ config.json"""
    config_path = get_resource_path('config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config = json.load(file)
            tasks = config.get('tasks', [])
            if not tasks:
                logging.warning("Không có task nào trong config.json")
            return tasks
    except FileNotFoundError:
        logging.error(f"File config.json không tồn tại tại {config_path}")
        return []
    except json.JSONDecodeError:
        logging.error("File config.json không đúng định dạng JSON")
        return []

# Setup logging
log_directory = os.path.join(os.path.expanduser("~"), "Documents")
os.makedirs(log_directory, exist_ok=True)
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
    """Đăng nhập nếu chưa đăng nhập (kiểm tra bằng editor)"""
    logging.info("Kiểm tra trạng thái đăng nhập...")
    try:
        # Nếu đã thấy editor thì coi như đã login
        WebDriverWait(sb.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.fr-element.fr-view[contenteditable='true']"))
        )
        logging.info("Đã đăng nhập từ trước")
        return True
    except TimeoutException:
        pass

    logging.info("Chưa đăng nhập, đang thực hiện đăng nhập...")
    try:
        username_field = WebDriverWait(sb.driver, 15).until(
            EC.element_to_be_clickable((By.NAME, "login"))
        )
        username_field.clear()
        username_field.send_keys(username)
        sb.sleep(random.uniform(1, 3))

        password_field = sb.driver.find_element(By.NAME, "password")
        password_field.clear()
        password_field.send_keys(password)
        sb.sleep(random.uniform(1, 3))

        try:
            remember_checkbox = sb.driver.find_element(By.NAME, "remember")
            if not remember_checkbox.is_selected():
                sb.execute_script("arguments[0].click();", remember_checkbox)
        except NoSuchElementException:
            pass

        login_button = WebDriverWait(sb.driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(@class, 'button--primary') and .//span[text()='Đăng nhập']]"))
        )
        sb.execute_script("arguments[0].scrollIntoView({block: 'center'});", login_button)
        sb.sleep(1)
        try:
            login_button.click()
        except ElementClickInterceptedException:
            sb.execute_script("arguments[0].click();", login_button)

        sb.sleep(random.uniform(4, 7))

        WebDriverWait(sb.driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.fr-element.fr-view[contenteditable='true']"))
        )
        logging.info("Đăng nhập thành công")
        return True
    except Exception as e:
        logging.error(f"Lỗi đăng nhập: {str(e)}")
        with open('login_error_page.html', 'w', encoding='utf-8') as f:
            f.write(sb.get_page_source())
        sb.save_screenshot('login_error.png')
        return False

def post_comment(sb, comment_text):
    """Đăng một bình luận"""
    logging.info(f"Đang đăng bình luận: {comment_text[:50]}...")
    try:
        editor = WebDriverWait(sb.driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.fr-element.fr-view[contenteditable='true']"))
        )
        contact_info = "Thanks"
        final_text = f"{comment_text}\n{contact_info}"

        sb.execute_script("arguments[0].scrollIntoView({block: 'center'});", editor)
        sb.sleep(random.uniform(1, 3))
        sb.execute_script("arguments[0].innerHTML = '';", editor)
        sb.execute_script("arguments[0].innerText = arguments[1];", editor, final_text)
        sb.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", editor)
        sb.sleep(random.uniform(1, 3))

        # Random scroll nhẹ
        sb.execute_script("window.scrollBy(0, 200);")
        sb.sleep(random.uniform(1, 2))

        submit_button = WebDriverWait(sb.driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@type='submit' and .//span[contains(text(), 'Trả lời')]]"))
        )
        sb.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
        sb.execute_script("arguments[0].click();", submit_button)

        sb.sleep(random.uniform(4, 8))

        # Đợi editor sẵn sàng lại cho lần sau
        WebDriverWait(sb.driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.fr-element.fr-view[contenteditable='true']"))
        )
        logging.info("Đăng bình luận thành công!")
        return True
    except Exception as e:
        logging.error(f"Lỗi khi đăng bình luận: {str(e)}")
        with open('post_error_page.html', 'w', encoding='utf-8') as f:
            f.write(sb.get_page_source())
        sb.save_screenshot('post_error.png')
        return False

def remove_first_comment_from_csv(csv_path):
    """Xóa dòng đầu tiên trong file CSV"""
    try:
        comments = []
        with open(csv_path, 'r', encoding='utf-8', newline='') as file:
            reader = csv.reader(file)
            comments = [row for row in reader if row and row[0].strip()]

        if not comments:
            logging.info(f"File {csv_path} đã trống")
            return

        with open(csv_path, 'w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(comments[1:])

        logging.info(f"Đã xóa bình luận đầu tiên khỏi {csv_path}")
    except Exception as e:
        logging.error(f"Lỗi xóa bình luận từ {csv_path}: {str(e)}")

def process_task(sb, task, username, password):
    """Xử lý một task: mở link → đăng nhập nếu cần → đăng 1 comment"""
    website_url = task['website_url']
    csv_path = get_resource_path(task['data_csv_path'])

    logging.info(f"=== Bắt đầu xử lý task: {website_url} ===")

    # Đọc comment đầu tiên
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            comments = [row[0].strip() for row in reader if row and row[0].strip()]
            if not comments:
                logging.warning(f"File {csv_path} trống, bỏ qua task này")
                return True
            comment = comments[0]
            logging.info(f"Bình luận sẽ đăng: {comment[:50]}...")
    except FileNotFoundError:
        logging.error(f"Không tìm thấy file CSV: {csv_path}")
        return False

    # Mở trang thread
    max_retries = 3
    for attempt in range(max_retries):
        sb.uc_open_with_reconnect(website_url, reconnect_time=20)
        sb.sleep(random.uniform(15, 25))

        if "Just a moment..." not in sb.get_title() and "Just a moment..." not in sb.get_page_source():
            break
        logging.warning(f"Cloudflare detected (lần {attempt+1})")
        sb.save_screenshot(f'cloudflare_{attempt+1}.png')
        if attempt == max_retries - 1:
            logging.error("Không thể bypass Cloudflare")
            return False

    # Đăng nhập nếu chưa
    if not login_to_website(sb, username, password):
        logging.error("Đăng nhập thất bại, bỏ qua task này")
        return False

    # Đăng bình luận
    if post_comment(sb, comment):
        remove_first_comment_from_csv(csv_path)
        logging.info(f"Hoàn thành task: {website_url}")
        return True
    else:
        logging.error(f"Đăng bình luận thất bại cho {website_url}")
        return False

def main():
    tasks = load_config()
    if not tasks:
        logging.error("Không có task nào để chạy. Kiểm tra config.json")
        return

    username = os.getenv('USERNAME')
    password = os.getenv('PASSWORD')
    if not username or not password:
        logging.error("Thiếu USERNAME hoặc PASSWORD trong environment variables")
        return

    with SB(uc=True, headless=True) as sb:
        success_count = 0
        for i, task in enumerate(tasks, 1):
            logging.info(f"Đang xử lý task {i}/{len(tasks)}")
            if process_task(sb, task, username, password):
                success_count += 1
            else:
                logging.warning(f"Task {i} thất bại, tiếp tục task tiếp theo")

            # Nghỉ giữa các task để tránh bị nghi ngờ
            if i < len(tasks):
                rest_time = random.uniform(30, 90)
                logging.info(f"Nghỉ {rest_time:.1f} giây trước task tiếp theo...")
                sb.sleep(rest_time)

        logging.info(f"Hoàn thành! Thành công: {success_count}/{len(tasks)} task")

if __name__ == "__main__":
    main()
