# whatsapp.py — FLOAT AI Desktop Assistant
# WhatsApp Web automation via Selenium for reliable message sending.

import os
import time
import logging
import threading
from pathlib import Path
from urllib.parse import quote

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    WebDriverException, StaleElementReferenceException,
)
from webdriver_manager.chrome import ChromeDriverManager

from config import WHATSAPP_SESSION_DIR, WHATSAPP_HEADLESS, log

logger = logging.getLogger("FLOAT.whatsapp")

# ─── Constants ────────────────────────────────────────────────────────────────
WHATSAPP_URL = "https://web.whatsapp.com"
QR_WAIT_TIMEOUT = 120       # seconds to wait for QR scan
CHAT_LOAD_TIMEOUT = 30      # seconds to wait for a chat to open
ELEMENT_TIMEOUT = 15        # general element wait

# ─── Module State ─────────────────────────────────────────────────────────────
_driver: webdriver.Chrome | None = None
_lock = threading.RLock()
_logged_in = False


# ─── Driver Management ───────────────────────────────────────────────────────
def _create_driver(headless: bool = False) -> webdriver.Chrome:
    """Create a Chrome WebDriver with persistent profile."""
    opts = Options()

    # Persistent profile so QR login survives restarts
    opts.add_argument(f"--user-data-dir={WHATSAPP_SESSION_DIR}")
    opts.add_argument("--profile-directory=Default")

    # Suppress noise
    opts.add_argument("--log-level=3")
    opts.add_argument("--disable-logging")
    opts.add_argument("--no-first-run")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])

    if headless:
        opts.add_argument("--headless=new")

    try:
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=opts)
        driver.set_page_load_timeout(60)
        logger.info("Chrome WebDriver created successfully")
        return driver
    except Exception as e:
        logger.error(f"Failed to create Chrome WebDriver: {e}")
        raise


def _get_driver() -> webdriver.Chrome | None:
    """Get or create the Chrome driver (lazy initialization)."""
    global _driver
    if _driver is not None:
        try:
            # Check if driver is still alive
            _ = _driver.title
            return _driver
        except Exception:
            logger.warning("Chrome session died, will re-create")
            _driver = None

    try:
        # First launch is always visible (user may need to scan QR)
        _driver = _create_driver(headless=False)
        return _driver
    except Exception as e:
        logger.error(f"Could not start Chrome: {e}")
        return None


# ─── Login & Session ─────────────────────────────────────────────────────────
def initialize_whatsapp() -> str:
    """
    Open WhatsApp Web and wait for login.
    On first use the user must scan the QR code with their phone.
    Returns a status message.
    """
    global _logged_in
    with _lock:
        driver = _get_driver()
        if driver is None:
            return "I couldn't start Chrome for WhatsApp. Is Chrome installed?"

        try:
            driver.get(WHATSAPP_URL)
            logger.info("Navigated to WhatsApp Web")
        except Exception as e:
            logger.error(f"Failed to load WhatsApp Web: {e}")
            return "I couldn't load WhatsApp Web. Please check your internet."

        # Check if already logged in (side panel visible)
        if _wait_for_login(timeout=15):
            _logged_in = True
            # Minimise after successful login
            try:
                driver.minimize_window()
            except Exception:
                pass
            logger.info("WhatsApp Web is logged in and ready")
            return "WhatsApp Web is ready."

        # Not logged in — user needs to scan QR
        logger.info("Waiting for QR code scan...")
        try:
            driver.maximize_window()
        except Exception:
            pass

        if _wait_for_login(timeout=QR_WAIT_TIMEOUT):
            _logged_in = True
            try:
                driver.minimize_window()
            except Exception:
                pass
            logger.info("QR code scanned — WhatsApp Web is ready")
            return "WhatsApp Web logged in successfully!"

        return ("I couldn't log in to WhatsApp Web. "
                "Please scan the QR code on the Chrome window and try again.")


def _wait_for_login(timeout: int = 30) -> bool:
    """Wait until WhatsApp Web shows the chat list (= logged in)."""
    driver = _driver
    if not driver:
        return False

    selectors = [
        (By.CSS_SELECTOR, "div#side"),
        (By.CSS_SELECTOR, "[data-testid='chat-list']"),
        (By.CSS_SELECTOR, "div[data-tab='3']"),
    ]

    for by, sel in selectors:
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, sel))
            )
            return True
        except TimeoutException:
            continue
    return False


def check_login_status() -> bool:
    """Return True if WhatsApp Web is logged in."""
    global _logged_in
    if not _driver:
        return False
    try:
        _driver.find_element(By.CSS_SELECTOR, "div#side")
        _logged_in = True
        return True
    except (NoSuchElementException, WebDriverException):
        _logged_in = False
        return False


# ─── Send Message (to phone number) ─────────────────────────────────────────
def send_message(phone_number: str, message: str) -> str:
    """
    Send a WhatsApp message to a phone number.
    phone_number must include country code, e.g. '+919876543210'.
    """
    with _lock:
        driver = _get_driver()
        if not driver:
            return "WhatsApp is not available. Chrome couldn't be started."

        # Ensure logged in
        if not _logged_in:
            result = initialize_whatsapp()
            if not _logged_in:
                return result

        # Clean phone number (keep only digits and leading +)
        clean_phone = phone_number.strip().replace(" ", "").replace("-", "")
        if not clean_phone.startswith("+"):
            clean_phone = "+" + clean_phone

        try:
            # Navigate to chat via URL (most reliable method)
            url = f"{WHATSAPP_URL}/send?phone={quote(clean_phone)}"
            driver.get(url)
            logger.info(f"Opening chat for {clean_phone}")

            # Wait for message input to appear (confirms chat loaded)
            msg_box = _wait_for_message_input(CHAT_LOAD_TIMEOUT)
            if not msg_box:
                # Check for "invalid phone number" popup
                if _check_invalid_phone():
                    return (f"The phone number {phone_number} doesn't seem to be "
                            "on WhatsApp.")
                return "I couldn't open the chat. Please try again."

            # Type the message (handle multi-line with Shift+Enter)
            _type_message(msg_box, message)

            # Press Enter to send
            msg_box.send_keys(Keys.ENTER)
            logger.info(f"Message sent to {clean_phone}")

            # Brief pause to let WhatsApp process
            time.sleep(1.5)
            return f"WhatsApp message sent successfully."

        except Exception as e:
            logger.error(f"Send message error: {e}")
            return "I couldn't send the WhatsApp message. Please try again."


# ─── Send Group Message ──────────────────────────────────────────────────────
def send_group_message(group_name: str, message: str) -> str:
    """Send a WhatsApp message to a group by searching for the group name."""
    with _lock:
        driver = _get_driver()
        if not driver:
            return "WhatsApp is not available."

        if not _logged_in:
            result = initialize_whatsapp()
            if not _logged_in:
                return result

        try:
            # Make sure we're on the main page
            driver.get(WHATSAPP_URL)
            time.sleep(2)

            # Find the search box
            search_box = _wait_for_element([
                (By.CSS_SELECTOR, "div[contenteditable='true'][data-tab='3']"),
                (By.CSS_SELECTOR, "[data-testid='chat-list-search']"),
            ], timeout=ELEMENT_TIMEOUT)

            if not search_box:
                return "I couldn't find the search box in WhatsApp."

            # Search for the group
            search_box.click()
            time.sleep(0.5)
            search_box.clear()
            search_box.send_keys(group_name)
            time.sleep(2)  # wait for search results

            # Click the first matching result
            try:
                result_item = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, f"//span[@title='{group_name}']")
                    )
                )
                result_item.click()
            except TimeoutException:
                # Try case-insensitive partial match
                try:
                    result_item = driver.find_element(
                        By.XPATH,
                        f"//span[contains(translate(@title,"
                        f"'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                        f"'abcdefghijklmnopqrstuvwxyz'),"
                        f"'{group_name.lower()}')]"
                    )
                    result_item.click()
                except NoSuchElementException:
                    return f"I couldn't find a group called '{group_name}'."

            time.sleep(1)

            # Type and send the message
            msg_box = _wait_for_message_input(ELEMENT_TIMEOUT)
            if not msg_box:
                return "I couldn't open the group chat."

            _type_message(msg_box, message)
            msg_box.send_keys(Keys.ENTER)
            logger.info(f"Group message sent to '{group_name}'")
            time.sleep(1.5)
            return f"Message sent to the {group_name} group."

        except Exception as e:
            logger.error(f"Group message error: {e}")
            return f"I couldn't send a message to the {group_name} group."


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _wait_for_message_input(timeout: int = 15):
    """Wait for the message input box to appear and return it."""
    selectors = [
        (By.CSS_SELECTOR, "div[contenteditable='true'][data-tab='10']"),
        (By.CSS_SELECTOR, "footer div[contenteditable='true']"),
        (By.XPATH, "//footer//div[@contenteditable='true']"),
    ]
    return _wait_for_element(selectors, timeout)


def _wait_for_element(selectors: list, timeout: int = 15):
    """Try multiple selectors and return the first element found."""
    driver = _driver
    if not driver:
        return None
    for by, sel in selectors:
        try:
            return WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, sel))
            )
        except TimeoutException:
            continue
    return None


def _type_message(element, message: str) -> None:
    """Type a message into an element, handling multi-line with Shift+Enter."""
    lines = message.split("\n")
    for i, line in enumerate(lines):
        element.send_keys(line)
        if i < len(lines) - 1:
            element.send_keys(Keys.SHIFT, Keys.ENTER)


def _check_invalid_phone() -> bool:
    """Check if WhatsApp is showing an 'invalid phone number' popup."""
    if not _driver:
        return False
    try:
        popup = _driver.find_element(
            By.XPATH,
            "//*[contains(text(), 'invalid') or contains(text(), 'Invalid')]"
        )
        return popup is not None
    except NoSuchElementException:
        return False


# ─── Cleanup ──────────────────────────────────────────────────────────────────
def close_whatsapp() -> None:
    """Shut down the Chrome driver."""
    global _driver, _logged_in
    with _lock:
        if _driver:
            try:
                _driver.quit()
                logger.info("Chrome WebDriver closed")
            except Exception as e:
                logger.warning(f"Error closing Chrome: {e}")
            finally:
                _driver = None
                _logged_in = False
