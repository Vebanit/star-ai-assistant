import time
from urllib.parse import quote_plus

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


DEFAULT_TIMEOUT = 45


def wait_for_any(driver, selectors, timeout=DEFAULT_TIMEOUT):
    end_time = time.time() + timeout
    last_error = None
    while time.time() < end_time:
        for by, value in selectors:
            try:
                elements = driver.find_elements(by, value)
                visible = [item for item in elements if item.is_displayed()]
                if visible:
                    return visible[0]
            except Exception as exc:
                last_error = exc
        time.sleep(0.5)
    if last_error:
        raise last_error
    return None


def open_whatsapp(driver, timeout=DEFAULT_TIMEOUT):
    driver.get("https://web.whatsapp.com")
    return whatsapp_status(driver, timeout=timeout)


def whatsapp_status(driver, timeout=12):
    search_selectors = [
        (By.XPATH, "//div[@contenteditable='true'][@role='textbox']"),
        (By.XPATH, "//div[@contenteditable='true'][@data-tab]"),
    ]
    qr_selectors = [
        (By.XPATH, "//*[contains(text(), 'Use WhatsApp on your computer')]"),
        (By.XPATH, "//*[contains(text(), 'Log into WhatsApp Web')]"),
        (By.CSS_SELECTOR, "canvas"),
    ]
    end_time = time.time() + timeout
    while time.time() < end_time:
        if wait_for_any(driver, search_selectors, timeout=0.2):
            return {"logged_in": True, "needs_login": False, "message": "WhatsApp Web is ready."}
        if wait_for_any(driver, qr_selectors, timeout=0.2):
            return {"logged_in": False, "needs_login": True, "message": "WhatsApp login is required. Scan the QR code in Chrome."}
        time.sleep(0.5)
    return {"logged_in": False, "needs_login": True, "message": "WhatsApp Web did not finish loading."}


def search_chat(driver, name, timeout=DEFAULT_TIMEOUT):
    search_box = wait_for_any(
        driver,
        [
            (By.XPATH, "//div[@contenteditable='true'][@role='textbox']"),
            (By.XPATH, "//div[@contenteditable='true'][@data-tab]"),
        ],
        timeout=timeout,
    )
    if not search_box:
        return False

    search_box.click()
    search_box.send_keys(Keys.CONTROL, "a")
    search_box.send_keys(str(name))
    time.sleep(1.5)
    search_box.send_keys(Keys.ENTER)
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab]"))
    )
    return True


def send_message(driver, contact, message, timeout=DEFAULT_TIMEOUT):
    status = open_whatsapp(driver, timeout=timeout)
    if status["needs_login"]:
        return status["message"]

    if not search_chat(driver, contact, timeout=timeout):
        return "WhatsApp search box was not found. Login may be required."

    message_boxes = [
        box for box in driver.find_elements(By.XPATH, "//div[@contenteditable='true'][@data-tab]")
        if box.is_displayed()
    ]
    if not message_boxes:
        return "WhatsApp message box was not found."

    box = message_boxes[-1]
    box.click()
    box.send_keys(message)
    box.send_keys(Keys.ENTER)
    return f"WhatsApp message sent to {contact}."


def open_chat(driver, contact, timeout=DEFAULT_TIMEOUT):
    status = open_whatsapp(driver, timeout=timeout)
    if status["needs_login"]:
        return status["message"]
    if search_chat(driver, contact, timeout=timeout):
        return f"Opened WhatsApp chat with {contact}."
    return "WhatsApp search box was not found. Login may be required."


def web_send_url(phone, message):
    clean_phone = "".join(char for char in str(phone) if char.isdigit())
    if not clean_phone:
        return None
    return f"https://wa.me/{clean_phone}?text={quote_plus(message)}"
