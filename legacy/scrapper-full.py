#!/usr/bin/env python3
"""
LinkedIn Enhanced Scraper - COMPLETELY FIXED VERSION
Features: Page memory, duplicate detection, coordinate clicking, RELIABLE contact extraction with CSS selectors
PART 1 of 6: Imports, Class Setup, and Initialization
"""

import requests
import time
import re
import json
import os
import shutil
import glob
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


class LinkedInEnhancedScraper:
    def __init__(self, output_dir="linkedin_enhanced_scrape", headless=False):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.headless = headless

        # WSL Downloads directory
        self.downloads_dir = Path.home() / "Downloads"

        # Page state tracking
        self.current_page = 1
        self.last_successful_page = 1
        self.base_search_url = None

        # Setup verbose logging
        self._setup_logging()

        # Setup browser
        self.driver = self._setup_browser()
        self.wait = WebDriverWait(self.driver, 15)

        # Setup requests session
        self._setup_requests_session()

        # Tracking variables
        self.processed_urls = set()
        self.existing_users = set()

        # Load existing users on startup
        self._load_existing_users()

        # Stats tracking
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped_existing": 0,
            "search_pages": 0,
            "profiles_found": 0,
            "contact_info_found": 0,
            "contact_info_attempts": 0,
            "contact_info_retries": 0,
            "emails_found": 0,
            "phones_found": 0,
            "websites_found": 0,
            "posts_found": 0,
            "comments_found": 0,
            "coordinate_clicks_successful": 0,
            "coordinate_clicks_failed": 0,
            "duplicates_skipped": 0,
            "page_recoveries": 0,
        }

        # FIXED: Add next folder number tracking
        self.next_folder_number = self._get_next_folder_number()

    def _setup_logging(self):
        """Setup verbose logging"""
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

        file_handler = logging.FileHandler(self.output_dir / "enhanced_scraper.log")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        self.logger.info(
            "🚀 LinkedIn Enhanced Scraper initialized - COMPLETELY FIXED VERSION"
        )
        self.logger.debug(f"📁 Output directory: {self.output_dir}")
        self.logger.debug(f"💾 Downloads directory: {self.downloads_dir}")

    def _get_next_folder_number(self):
        """Find the highest existing folder number and return the next one"""
        try:
            existing_folders = [d for d in self.output_dir.iterdir() if d.is_dir()]
            max_number = 0

            for folder in existing_folders:
                folder_name = folder.name
                # Check if folder starts with a number
                if "_" in folder_name:
                    first_part = folder_name.split("_")[0]
                    if first_part.isdigit():
                        number = int(first_part)
                        max_number = max(max_number, number)

            next_number = max_number + 1
            self.logger.info(
                f"📊 Found max folder number: {max_number}, next will be: {next_number}"
            )
            return next_number

        except Exception as e:
            self.logger.error(f"❌ Error getting next folder number: {e}")
            return 1

    def _load_existing_users(self):
        """Load existing user names from folders to avoid re-processing - FIXED VERSION"""
        try:
            existing_folders = [d for d in self.output_dir.iterdir() if d.is_dir()]

            for folder in existing_folders:
                folder_name = folder.name

                # Handle both "1_John_Doe" and "John_Doe" formats
                if "_" in folder_name and folder_name.split("_")[0].isdigit():
                    # Remove number prefix: "1_John_Doe" -> "John_Doe"
                    user_name = "_".join(folder_name.split("_")[1:])
                else:
                    # No number prefix: "John_Doe" -> "John_Doe"
                    user_name = folder_name

                # Clean and normalize the name - FIXED
                clean_name = self._normalize_name(user_name)
                self.existing_users.add(clean_name)

                # Debug logging to see what we're loading
                self.logger.debug(
                    f"🔍 Loaded existing user: '{user_name}' -> normalized: '{clean_name}'"
                )

            self.logger.info(f"📋 Loaded {len(self.existing_users)} existing users")

        except Exception as e:
            self.logger.error(f"❌ Error loading existing users: {e}")

    def _normalize_name(self, name):
        """Normalize name for consistent comparison - FIXED VERSION"""
        # Remove all non-alphanumeric characters and convert to lowercase
        # Keep spaces temporarily, then convert to single format
        clean = re.sub(r"[^\w\s]", "", name.lower().strip())
        # Replace multiple spaces with single space, then convert to underscore
        clean = re.sub(r"\s+", "_", clean)
        return clean

    def _user_already_exists(self, profile_name):
        """Check if user already exists by name"""
        normalized_name = self._normalize_name(profile_name)
        exists = normalized_name in self.existing_users

        if exists:
            self.logger.info(f"👤 User already exists: {profile_name}")

        return exists

    """
LinkedIn Enhanced Scraper - COMPLETELY FIXED VERSION
PART 2 of 6: State Management, Browser Setup, Session Management
"""

    def _save_page_state(self):
        """Save current page state to file for recovery - FIXED VERSION"""
        try:
            state_file = self.output_dir / "page_state.json"
            state = {
                "current_page": self.current_page,
                "last_successful_page": self.last_successful_page,
                "base_search_url": self.base_search_url,
                "processed_urls": list(self.processed_urls),
                "existing_users": list(self.existing_users),
                "next_folder_number": self.next_folder_number,  # FIXED: Add this
                "saved_at": datetime.now().isoformat(),
            }

            with open(state_file, "w") as f:
                json.dump(state, f, indent=2)

            self.logger.debug(
                f"💾 Page state saved: Page {self.current_page}, Next folder: {self.next_folder_number}"
            )

        except Exception as e:
            self.logger.error(f"❌ Error saving page state: {e}")

    def _load_page_state(self):
        """Load page state from file for recovery - FIXED VERSION"""
        try:
            state_file = self.output_dir / "page_state.json"

            if state_file.exists():
                with open(state_file, "r") as f:
                    state = json.load(f)

                self.current_page = state.get("current_page", 1)
                self.last_successful_page = state.get("last_successful_page", 1)
                self.base_search_url = state.get("base_search_url")
                self.processed_urls = set(state.get("processed_urls", []))

                # FIXED: Load folder number from state, or calculate if missing
                self.next_folder_number = state.get(
                    "next_folder_number", self._get_next_folder_number()
                )

                # Merge with existing users
                saved_users = set(state.get("existing_users", []))
                self.existing_users.update(saved_users)

                self.logger.info(
                    f"📥 Page state loaded: Page {self.current_page}, Next folder: {self.next_folder_number}"
                )
                return True

        except Exception as e:
            self.logger.error(f"❌ Error loading page state: {e}")

        return False

    def _setup_browser(self):
        """Setup Chrome browser with visible mouse cursor"""
        self.logger.debug("🌐 Setting up Chrome browser...")

        options = ChromeOptions()

        prefs = {
            "download.default_directory": str(self.downloads_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": True,
        }
        options.add_experimental_option("prefs", prefs)

        if self.headless:
            options.add_argument("--headless")
        else:
            self.logger.info(
                "🌐 Starting browser - please log in manually when prompted"
            )

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        driver = webdriver.Chrome(options=options)
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        # Add CSS to make mouse cursor more visible
        driver.execute_script(
            """
            var style = document.createElement('style');
            style.innerHTML = '*{cursor: crosshair !important;}';
            document.head.appendChild(style);
        """
        )

        self.logger.debug("✅ Chrome browser setup complete")
        return driver

    def _setup_requests_session(self):
        """Setup requests session"""
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

    def _coordinate_click(self, x, y, description="", move_slow=True):
        """Click at specific coordinates with visible mouse movement"""
        try:
            self.logger.info(f"🎯 Moving mouse to coordinates ({x}, {y}) {description}")

            # Create visible mouse movement
            actions = ActionChains(self.driver)

            if move_slow:
                actions.move_by_offset(x, y)
                actions.pause(0.5)
            else:
                actions.move_by_offset(x, y)

            actions.click()
            actions.pause(0.3)
            actions.perform()

            self.logger.info(f"🔘 Clicked at ({x}, {y})")

            # Reset mouse position
            actions = ActionChains(self.driver)
            actions.move_by_offset(-x, -y)
            actions.perform()

            time.sleep(2)
            return True

        except Exception as e:
            self.logger.error(f"❌ Coordinate click failed: {e}")
            return False

    def _check_current_state(self):
        """Check what type of page we're currently on"""
        try:
            current_url = self.driver.current_url.lower()

            if "/in/" in current_url:
                return "profile"
            elif "/search/" in current_url:
                return "search"
            else:
                return "unknown"

        except Exception as e:
            self.logger.error(f"❌ Error checking current state: {e}")
            return "unknown"

    def _build_page_url(self, page_num):
        """Build search URL for specific page"""
        if not self.base_search_url:
            return None

        # Parse current URL and add/update page parameter
        if "&page=" in self.base_search_url:
            base_url = re.sub(r"&page=\d+", f"&page={page_num}", self.base_search_url)
        elif "?page=" in self.base_search_url:
            base_url = re.sub(r"\?page=\d+", f"?page={page_num}", self.base_search_url)
        else:
            separator = "&" if "?" in self.base_search_url else "?"
            base_url = f"{self.base_search_url}{separator}page={page_num}"

        return base_url

    def _recover_to_specific_page(self, page_num):
        """Recover to specific page using stored URL"""
        try:
            self.logger.warning(f"🔄 Attempting recovery to page {page_num}...")
            self.stats["page_recoveries"] += 1

            page_url = self._build_page_url(page_num)

            if page_url:
                self.logger.info(f"🔄 Navigating to page {page_num}: {page_url}")
                self.driver.get(page_url)
                time.sleep(3)

                if self._check_current_state() == "search":
                    self.current_page = page_num
                    self._save_page_state()
                    self.logger.info(f"✅ Successfully recovered to page {page_num}")
                    return True
                else:
                    self.logger.error(f"❌ Recovery failed - not on search page")
                    return False
            else:
                self.logger.error("❌ No base search URL available")
                return False

        except Exception as e:
            self.logger.error(f"❌ Error during page recovery: {e}")
            return False

    def _sync_cookies(self):
        """Sync cookies from browser to requests session"""
        try:
            self.session.cookies.clear()
            for cookie in self.driver.get_cookies():
                self.session.cookies.set(
                    cookie["name"],
                    cookie["value"],
                    domain=cookie.get("domain", ".linkedin.com"),
                )
        except Exception as e:
            self.logger.error(f"❌ Error syncing cookies: {e}")

    def _is_logged_in(self):
        """Check if currently logged in to LinkedIn"""
        try:
            current_url = self.driver.current_url.lower()

            logged_in_patterns = [
                "linkedin.com/feed",
                "linkedin.com/in/",
                "linkedin.com/mynetwork",
                "linkedin.com/messaging",
                "linkedin.com/jobs",
                "linkedin.com/search",
            ]

            for pattern in logged_in_patterns:
                if pattern in current_url:
                    return True

            logout_indicators = [
                "button[aria-label*='Sign out']",
                "a[href*='logout']",
                ".global-nav__me",
                "img[alt*='profile']",
            ]

            for selector in logout_indicators:
                if self.driver.find_elements(By.CSS_SELECTOR, selector):
                    return True

            return False

        except Exception as e:
            self.logger.error(f"❌ Error checking login status: {e}")
            return False

    """
LinkedIn Enhanced Scraper - COMPLETELY FIXED VERSION
PART 3 of 6: Contact Information Extraction System (COMPLETELY REWRITTEN)
"""

    def _is_valid_email(self, email):
        """Validate email format"""
        try:
            if not email or len(email) < 5:
                return False
            pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            return re.match(pattern, email) is not None
        except:
            return False

    def _is_valid_phone(self, phone):
        """Validate phone number format"""
        try:
            if not phone:
                return False
            clean_phone = re.sub(r"[^\d+\-\(\)\s]", "", phone)
            digits = re.findall(r"\d", clean_phone)
            return len(digits) >= 7
        except:
            return False

    def _is_valid_website(self, url):
        """Validate website URL format - FIXED with LinkedIn filtering"""
        try:
            if not url or len(url) < 10:
                return False
            if not url.lower().startswith(("http://", "https://")):
                return False
            if "." not in url:
                return False

            # Skip patterns - including ALL LinkedIn URLs
            skip_patterns = [
                "mailto:",
                "tel:",
                "javascript:",
                "linkedin.com/",  # This will catch ALL LinkedIn URLs
                "www.linkedin.com/",  # Extra safety for www variant
            ]

            for pattern in skip_patterns:
                if pattern in url.lower():
                    return False
            return True
        except Exception:
            return False

    def _find_contact_button(self):
        """Find contact info button using tested reliable CSS selectors"""
        # Top 3 most reliable selectors from testing
        contact_selectors = [
            {
                "name": "CSS ID (Most Reliable)",
                "method": By.CSS_SELECTOR,
                "selector": "#top-card-text-details-contact-info",
            },
            {
                "name": "CSS Class Backup",
                "method": By.CSS_SELECTOR,
                "selector": "a.link-without-visited-state",
            },
            {
                "name": "CSS Href Backup",
                "method": By.CSS_SELECTOR,
                "selector": 'a[href*="contact-info"]',
            },
        ]

        for selector_info in contact_selectors:
            try:
                self.logger.debug(f"🔍 Testing: {selector_info['name']}")
                self.logger.debug(f"   Selector: {selector_info['selector']}")

                elements = self.driver.find_elements(
                    selector_info["method"], selector_info["selector"]
                )

                if not elements:
                    self.logger.debug(f"   ❌ No elements found")
                    continue

                # Check for clickable elements
                for element in elements:
                    try:
                        if element.is_displayed() and element.is_enabled():
                            text = element.text.strip()
                            href = element.get_attribute("href") or "No href"
                            self.logger.debug(
                                f"   ✅ Found clickable element: text='{text}', href='{href[:50]}...'"
                            )
                            self.logger.info(f"   🎯 Using: {selector_info['name']}")
                            return element, selector_info["name"]
                    except Exception as e:
                        continue

                self.logger.debug(f"   ⚠️ Elements found but none clickable")

            except Exception as e:
                self.logger.debug(f"   ❌ Selector failed: {e}")
                continue

        return None, None

    def _extract_contact_info_from_modal(self):
        """Extract email, phone, websites from opened contact modal - COMPLETELY REWRITTEN"""
        contact_data = {
            "email": None,
            "phone": None,
            "websites": [],
            "extraction_details": {},
        }

        self.logger.info("📞 Extracting contact information from modal...")

        # Wait for modal to fully load
        time.sleep(3)

        # EMAIL EXTRACTION - Multiple CSS strategies
        email_selectors = [
            # Direct email links
            "a[href*='mailto:']",
            # Common email container patterns
            "section div a[href*='mailto']",
            # Text scanning in likely email sections
            "section:nth-child(4) div a",
            "section:last-child div a",
        ]

        for i, selector in enumerate(email_selectors):
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    href = element.get_attribute("href")
                    text = element.text.strip()

                    self.logger.debug(
                        f"🔍 Email selector {i+1}: href='{href}', text='{text}'"
                    )

                    if href and "mailto:" in href:
                        email = href.replace("mailto:", "").strip()
                        if self._is_valid_email(email):
                            contact_data["email"] = email
                            contact_data["extraction_details"][
                                "email_method"
                            ] = f"CSS selector {i+1}: {selector}"
                            self.logger.info(f"📧 EMAIL FOUND: {email}")
                            self.stats["emails_found"] += 1
                            break
                    elif text and "@" in text and self._is_valid_email(text):
                        contact_data["email"] = text
                        contact_data["extraction_details"][
                            "email_method"
                        ] = f"CSS text {i+1}: {selector}"
                        self.logger.info(f"📧 EMAIL FOUND: {text}")
                        self.stats["emails_found"] += 1
                        break

                if contact_data["email"]:
                    break
            except Exception as e:
                self.logger.debug(f"🔍 Email selector {i+1} failed: {e}")
                continue

        # PHONE EXTRACTION - Multiple CSS strategies
        phone_selectors = [
            # Direct phone links
            "a[href*='tel:']",
            # Common phone container patterns - trying various sections
            "section:nth-child(3) ul li span",
            "section:nth-child(3) ul li",
            "section div ul li span",
            # Broader phone text search
            "*[data-test*='phone']",
            "*[aria-label*='phone']",
        ]

        for i, selector in enumerate(phone_selectors):
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    href = element.get_attribute("href")
                    text = element.text.strip()

                    self.logger.debug(
                        f"🔍 Phone selector {i+1}: href='{href}', text='{text}'"
                    )

                    if href and "tel:" in href:
                        phone = href.replace("tel:", "").strip()
                        if self._is_valid_phone(phone):
                            contact_data["phone"] = phone
                            contact_data["extraction_details"][
                                "phone_method"
                            ] = f"CSS href {i+1}: {selector}"
                            self.logger.info(f"📱 PHONE FOUND: {phone}")
                            self.stats["phones_found"] += 1
                            break
                    elif text and self._is_valid_phone(text):
                        contact_data["phone"] = text
                        contact_data["extraction_details"][
                            "phone_method"
                        ] = f"CSS text {i+1}: {selector}"
                        self.logger.info(f"📱 PHONE FOUND: {text}")
                        self.stats["phones_found"] += 1
                        break

                if contact_data["phone"]:
                    break
            except Exception as e:
                self.logger.debug(f"🔍 Phone selector {i+1} failed: {e}")
                continue

        # WEBSITE EXTRACTION - Multiple CSS strategies with LinkedIn filtering
        website_selectors = [
            # Common website container patterns
            "section:nth-child(2) ul li a",
            "section:nth-child(2) div a",
            "section div ul li a",
            # Any external links (excluding mailto/tel/linkedin)
            "a[href^='http']",
        ]

        for i, selector in enumerate(website_selectors):
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    href = element.get_attribute("href")
                    text = element.text.strip()

                    self.logger.debug(
                        f"🔍 Website selector {i+1}: href='{href}', text='{text}'"
                    )

                    if href and self._is_valid_website(href):
                        website_data = {
                            "url": href,
                            "display_text": text if text else href,
                            "extraction_method": f"CSS {i+1}: {selector}",
                        }

                        # Avoid duplicates
                        if not any(w["url"] == href for w in contact_data["websites"]):
                            contact_data["websites"].append(website_data)
                            self.logger.info(f"🌐 WEBSITE FOUND: {href}")
                            self.stats["websites_found"] += 1

            except Exception as e:
                self.logger.debug(f"🔍 Website selector {i+1} failed: {e}")
                continue

        # Final summary
        self.logger.info(f"📊 EXTRACTION SUMMARY:")
        self.logger.info(
            f"📧 Email: {contact_data['email'] if contact_data['email'] else 'Not found'}"
        )
        self.logger.info(
            f"📱 Phone: {contact_data['phone'] if contact_data['phone'] else 'Not found'}"
        )
        self.logger.info(f"🌐 Websites: {len(contact_data['websites'])} found")

        return contact_data

    def _close_contact_modal(self):
        # """Close contact info modal if open - FIXED VERSION"""
        try:
            self.logger.debug("🔍 Attempting to close contact modal...")

            # Multiple strategies to close modal
            close_selectors = [
                # Most common close button patterns
                "button[aria-label*='Close']",
                "button[aria-label*='close']",
                ".artdeco-modal__dismiss",
                "[data-test-modal-close-btn]",
                ".artdeco-modal-overlay button[aria-label*='Close']",
                "button.artdeco-modal__dismiss",
                # Generic close patterns
                ".modal-close",
                ".close-button",
                "[role='button'][aria-label*='Close']",
                # Escape patterns
                ".artdeco-modal-overlay",  # Click overlay to close
            ]

            modal_closed = False
            for i, selector in enumerate(close_selectors):
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)

                    for element in elements:
                        try:
                            if element.is_displayed() and element.is_enabled():
                                self.logger.debug(
                                    f"🔘 Trying close method {i+1}: {selector}"
                                )
                                element.click()
                                modal_closed = True
                                time.sleep(1)  # Wait for modal to close
                                break
                        except Exception as e:
                            continue

                    if modal_closed:
                        break

                except Exception as e:
                    continue

            # Try pressing Escape key as fallback
            if not modal_closed:
                try:
                    self.logger.debug("🔑 Trying Escape key to close modal...")
                    from selenium.webdriver.common.keys import Keys

                    self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                    modal_closed = True
                    time.sleep(1)
                except Exception as e:
                    pass

            if modal_closed:
                self.logger.debug("✅ Contact modal closed successfully")
            else:
                self.logger.warning("⚠️ Could not close contact modal")

            return modal_closed

        except Exception as e:
            self.logger.error(f"❌ Error closing contact modal: {e}")
            return False

    def extract_contact_info_reliable(self, profile_url):
        """COMPLETELY REWRITTEN: Extract contact information using tested reliable methods"""
        try:
            self.logger.info("📞 Starting RELIABLE contact information extraction...")
            self.stats["contact_info_attempts"] += 1

            contact_info = {
                "email": None,
                "phone": None,
                "websites": [],
                "social_profiles": [],
                "extraction_attempts": 0,
                "extraction_method": None,
            }

            # Try extraction twice with different strategies
            for attempt in range(1, 3):
                contact_info["extraction_attempts"] = attempt
                self.logger.info(f"📞 Contact info extraction attempt {attempt}/2")

                if attempt > 1:
                    self.stats["contact_info_retries"] += 1
                    self.logger.info("🔄 Retrying contact info extraction...")

                # Find contact button using tested reliable selectors
                contact_button, button_method = self._find_contact_button()

                if not contact_button:
                    self.logger.warning(
                        f"⚠️ Attempt {attempt}: No contact button found"
                    )
                    time.sleep(2)
                    continue

                # Click the contact button
                try:
                    self.logger.info(
                        f"🔘 Attempt {attempt}: Clicking contact info button..."
                    )
                    contact_button.click()
                    time.sleep(5)  # Wait longer for modal to load

                    contact_info["extraction_method"] = button_method

                    # Extract using CSS-based extraction
                    extracted_data = self._extract_contact_info_from_modal()

                    # Merge extracted data
                    if extracted_data["email"]:
                        contact_info["email"] = extracted_data["email"]
                    if extracted_data["phone"]:
                        contact_info["phone"] = extracted_data["phone"]
                    if extracted_data["websites"]:
                        contact_info["websites"].extend(extracted_data["websites"])

                    # Close the modal
                    self._close_contact_modal()

                    extracted_any = (
                        contact_info["email"]
                        or contact_info["phone"]
                        or contact_info["websites"]
                    )

                    if extracted_any:
                        self.logger.info(
                            f"✅ Contact info extraction successful on attempt {attempt}"
                        )
                        break
                    else:
                        self.logger.warning(
                            f"⚠️ Attempt {attempt}: No contact info found in modal"
                        )

                except Exception as e:
                    self.logger.error(
                        f"❌ Attempt {attempt}: Error clicking contact button: {e}"
                    )
                    self._close_contact_modal()  # Try to close any open modal
                    continue

            # Final validation and stats
            if (
                contact_info["email"]
                or contact_info["phone"]
                or contact_info["websites"]
            ):
                self.stats["contact_info_found"] += 1
                self.logger.info(
                    f"✅ Contact extraction complete: Email={bool(contact_info['email'])}, Phone={bool(contact_info['phone'])}, Websites={len(contact_info['websites'])}"
                )
            else:
                self.logger.warning(
                    "⚠️ No contact information extracted after all attempts"
                )

            return contact_info

        except Exception as e:
            self.logger.error(f"❌ Error in reliable contact info extraction: {e}")
            return {
                "email": None,
                "phone": None,
                "websites": [],
                "social_profiles": [],
                "extraction_attempts": 0,
                "extraction_method": "error",
            }

    """
LinkedIn Enhanced Scraper - COMPLETELY FIXED VERSION
PART 4 of 6: Profile Extraction, Authentication, and Search Setup
"""

    def _extract_name_quickly(self):
        """Quickly extract name from current profile to check if it exists"""
        try:
            name_selectors = [
                "h1.text-heading-xlarge",
                "h1",
                ".pv-text-details__left-panel h1",
            ]

            for selector in name_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    name = element.text.strip()
                    if name and len(name) > 2:
                        return name
                except:
                    continue

            return "Unknown"

        except Exception as e:
            self.logger.error(f"❌ Error extracting name quickly: {e}")
            return "Unknown"

    def extract_profile_info(self, profile_url):
        """Extract comprehensive profile information with RELIABLE contact info"""
        try:
            name = "Unknown"
            headline = "No headline"
            location = "Unknown location"

            # Name extraction
            name_selectors = [
                "h1.text-heading-xlarge",
                "h1",
                ".pv-text-details__left-panel h1",
            ]

            for selector in name_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    name = element.text.strip()
                    if name and len(name) > 2:
                        break
                except:
                    continue

            # Headline extraction
            headline_selectors = [
                ".text-body-medium.break-words",
                ".pv-text-details__left-panel .text-body-medium",
            ]

            for selector in headline_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    headline = element.text.strip()
                    if headline and len(headline) > 3:
                        break
                except:
                    continue

            # Location extraction
            location_selectors = [
                ".text-body-small.inline.t-black--light.break-words",
                ".pv-text-details__left-panel .text-body-small",
            ]

            for selector in location_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        if text and any(
                            word in text.lower()
                            for word in ["united states", "usa", "us"]
                        ):
                            location = text
                            break
                    if location != "Unknown location":
                        break
                except:
                    continue

            # RELIABLE contact info extraction using our tested system
            contact_info = self.extract_contact_info_reliable(profile_url)

            profile_info = {
                "name": name,
                "headline": headline,
                "location": location,
                "url": profile_url,
                "contact_info": contact_info,
                "scraped_at": datetime.now().isoformat(),
            }

            self.logger.info(f"✅ Profile: {name} - {headline[:50]}")
            return profile_info

        except Exception as e:
            self.logger.error(f"❌ Error extracting profile: {e}")
            return {
                "name": "Unknown",
                "headline": "Error",
                "location": "Unknown",
                "url": profile_url,
                "contact_info": {
                    "email": None,
                    "phone": None,
                    "websites": [],
                    "social_profiles": [],
                },
            }

    def wait_for_manual_login(self):
        """Wait for user to complete manual login"""
        try:
            self.logger.info("🔐 Navigating to LinkedIn...")

            self.driver.get("https://www.linkedin.com/login")
            time.sleep(3)

            if self._is_logged_in():
                self.logger.info("✅ Already logged in!")
                self._sync_cookies()
                return True

            print("\n" + "=" * 60)
            print("🔐 PLEASE LOG IN TO LINKEDIN MANUALLY")
            print("=" * 60)
            print("👆 Use the browser window that just opened")
            print("📧 Enter your email and password")
            print("🔐 Complete any 2FA, captcha, etc.")
            print("⏳ Take as much time as you need!")
            print("🤖 The script will automatically detect when you're logged in")
            print("=" * 60)

            max_wait = 900  # 15 minutes
            check_interval = 5
            waited = 0

            while waited < max_wait:
                time.sleep(check_interval)
                waited += check_interval

                if self._is_logged_in():
                    print("\n✅ LOGIN SUCCESSFUL!")
                    self.logger.info("✅ Login detected! Syncing cookies...")
                    self._sync_cookies()

                    self.driver.get("https://www.linkedin.com/feed/")
                    time.sleep(3)

                    if self._is_logged_in():
                        self.logger.info("✅ Login confirmed - ready to scrape!")
                        return True

                if waited % 30 == 0:
                    minutes_left = (max_wait - waited) // 60
                    print(
                        f"⏳ Still waiting for login... {minutes_left} minutes remaining"
                    )

            print("\n❌ Login timeout after 15 minutes")
            return False

        except Exception as e:
            self.logger.error(f"❌ Login wait error: {e}")
            return False

    def setup_manual_search_filters(self):
        """Search for 'author' and wait 15 seconds for manual filter selection"""
        try:
            self.logger.info("🔍 Setting up search with manual filter selection...")

            search_url = "https://www.linkedin.com/search/results/all/?keywords=author&origin=SWITCH_SEARCH_VERTICAL"
            self.logger.debug(f"📄 Navigating to: {search_url}")
            self.driver.get(search_url)
            time.sleep(5)

            print("\n" + "=" * 80)
            print("🔍 SEARCH PAGE LOADED - PLEASE SET FILTERS MANUALLY")
            print("=" * 80)
            print("👆 Use the browser window to set these filters:")
            print("   1. 🔘 Click 'All filters' button")
            print("   2. 🔗 Click '2nd' connection level")
            print("   3. 🇺🇸 Click 'United States' checkbox")
            print("   4. 📊 Click 'Show results' button")
            print("")
            print("⏳ You have 15 seconds to complete this...")
            print("🤖 The script will automatically continue after 15 seconds")
            print("=" * 80)

            # Wait 15 seconds for manual filter selection
            for i in range(15, 0, -1):
                print(f"⏱️  {i} seconds remaining...")
                time.sleep(1)

            print("\n✅ Manual filter selection time complete!")
            self.logger.info(
                "✅ Manual filter selection period finished - continuing with scraping"
            )

            # Store base search URL
            self.base_search_url = self.driver.current_url
            self.logger.info(f"📍 Base search URL stored: {self.base_search_url}")

            time.sleep(3)
            return True

        except Exception as e:
            self.logger.error(f"❌ Error in manual search setup: {e}")
            return False

    def _clean_filename(self, name):
        """Clean name for safe folder/filename"""
        clean = re.sub(r'[<>:"/\\|?*]', "_", name.strip())
        clean = re.sub(r"[^\w\s-]", "", clean)
        clean = re.sub(r"\s+", "_", clean)
        return clean[:50]

    def scrape_current_profile(self):
        # """Scrape the currently loaded profile page with comprehensive data extraction - FIXED VERSION"""
        try:
            current_url = self.driver.current_url
            self.logger.info(f"📋 Scraping current profile: {current_url}")

            # Extract profile info (includes RELIABLE contact info)
            profile_info = self.extract_profile_info(current_url)

            # Create folder with FIXED numbering system
            clean_name = self._clean_filename(
                f"{self.next_folder_number}_{profile_info['name']}"
            )
            person_folder = self.output_dir / clean_name
            person_folder.mkdir(exist_ok=True)

            # INCREMENT the folder number for next use
            self.next_folder_number += 1

            # Save profile info
            info_path = person_folder / "profile_info.json"
            with open(info_path, "w", encoding="utf-8") as f:
                json.dump(profile_info, f, indent=2, ensure_ascii=False)

            # Download components
            pdf_success = self.download_profile_pdf(current_url, person_folder)
            time.sleep(2)

            picture_success = self.download_profile_picture(current_url, person_folder)
            time.sleep(2)

            activity_success = self.scrape_enhanced_activity(current_url, person_folder)
            time.sleep(2)

            results = {
                "profile_info": True,
                "pdf": pdf_success,
                "picture": picture_success,
                "activity": activity_success,
            }

            success_count = sum(1 for v in results.values() if v == True)
            if success_count >= 3:
                self.stats["successful"] += 1
                status = "✅ SUCCESS"
            else:
                self.stats["failed"] += 1
                status = "⚠️ PARTIAL"

            # FIXED: Enhanced logging with correct contact info stats
            contact_info = profile_info.get("contact_info", {})
            email_found = bool(contact_info.get("email"))
            phone_found = bool(contact_info.get("phone"))
            websites_found = len(contact_info.get("websites", []))

            # Debug the contact info to see what we actually have
            self.logger.debug(f"🔍 Contact info debug: {contact_info}")
            self.logger.debug(f"🔍 Email: {contact_info.get('email')}")
            self.logger.debug(f"🔍 Phone: {contact_info.get('phone')}")
            self.logger.debug(f"🔍 Websites: {contact_info.get('websites', [])}")

            contact_summary = f"E:{email_found}, P:{phone_found}, W:{websites_found}"

            self.logger.info(
                f"{status} [{self.next_folder_number-1}] {clean_name} - {success_count}/4 - Contact: {contact_summary}"
            )

            return results

        except Exception as e:
            self.stats["failed"] += 1
            self.logger.error(f"❌ Error scraping current profile: {e}")

    """
LinkedIn Enhanced Scraper - COMPLETELY FIXED VERSION
PART 5 of 6: Downloads Management and Activity Scraping
"""

    def _move_downloaded_pdf(self, person_folder, expected_name="Profile.pdf"):
        """Move downloaded PDF from ~/Downloads to person folder"""
        try:
            pdf_patterns = [
                self.downloads_dir / expected_name,
                self.downloads_dir / "Profile*.pdf",
                self.downloads_dir / "*.pdf",
            ]

            downloaded_pdf = None
            for pattern in pdf_patterns:
                if isinstance(pattern, Path) and pattern.exists():
                    downloaded_pdf = pattern
                    break
                else:
                    files = list(self.downloads_dir.glob(pattern.name))
                    if files:
                        downloaded_pdf = max(files, key=os.path.getctime)
                        break

            if downloaded_pdf and downloaded_pdf.exists():
                destination = person_folder / "profile.pdf"
                shutil.move(str(downloaded_pdf), str(destination))
                self.logger.info(f"✅ PDF moved: {destination}")
                return True
            else:
                self.logger.warning(f"⚠️ No PDF found in downloads")
                return False

        except Exception as e:
            self.logger.error(f"❌ Error moving PDF: {e}")
            return False

    def download_profile_pdf(self, profile_url, output_folder):
        """Download profile as PDF"""
        try:
            self.logger.info("📄 Downloading PDF...")

            # Clear old PDFs
            existing_pdfs = list(self.downloads_dir.glob("Profile*.pdf"))
            for pdf in existing_pdfs:
                try:
                    pdf.unlink()
                except:
                    pass

            # Find More actions button
            more_selectors = [
                "button[aria-label*='More actions']",
                "button[id*='profile-overflow-action']",
            ]

            more_button = None
            for selector in more_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            more_button = element
                            break
                    if more_button:
                        break
                except:
                    continue

            if more_button:
                self.logger.info("🔘 Clicking More actions...")
                more_button.click()
                time.sleep(2)

                # Find PDF option by text
                pdf_selectors = [
                    "div[role='menuitem']",
                    "button[role='menuitem']",
                    ".artdeco-dropdown__item",
                ]

                pdf_clicked = False
                for selector in pdf_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if element.is_displayed() and "PDF" in element.text:
                                self.logger.info("📄 Clicking PDF option...")
                                element.click()
                                time.sleep(5)  # Wait for download
                                pdf_clicked = True
                                break
                        if pdf_clicked:
                            break
                    except:
                        continue

                if pdf_clicked:
                    return self._move_downloaded_pdf(output_folder)

            return False

        except Exception as e:
            self.logger.error(f"❌ PDF download error: {e}")
            return False

    def download_profile_picture(self, profile_url, output_folder):
        """Download profile picture"""
        try:
            self.logger.info("🖼️ Downloading profile picture...")

            img_selectors = [
                "img.pv-top-card-profile-picture__image--show",
                "img.evi-image",
                "img[alt*='profile']",
            ]

            img_url = None
            for selector in img_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            src = element.get_attribute("src")
                            if src and "profile" in src:
                                img_url = src
                                break
                    if img_url:
                        break
                except:
                    continue

            if not img_url:
                self.logger.warning("⚠️ No profile picture found")
                return False

            # Download
            self._sync_cookies()
            response = self.session.get(img_url, timeout=30)
            response.raise_for_status()

            ext = (
                ".jpg" if "jpg" in response.headers.get("content-type", "") else ".png"
            )
            img_path = output_folder / f"profile_picture{ext}"

            with open(img_path, "wb") as f:
                f.write(response.content)

            self.logger.info(f"✅ Profile picture saved: {img_path}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Profile picture error: {e}")
            return False

    def scrape_enhanced_activity(self, profile_url, output_folder):
        """Enhanced activity scraping with posts and comments"""
        try:
            self.logger.info("📈 Starting enhanced activity scraping...")

            activity_data = {
                "profile_url": profile_url,
                "scraped_at": datetime.now().isoformat(),
                "posts": [],
                "comments": [],
            }

            # Navigate to activity page
            activity_url = f"{profile_url.rstrip('/')}/recent-activity/all/"
            self.logger.debug(f"📍 Going to: {activity_url}")
            self.driver.get(activity_url)
            time.sleep(3)

            # Look for activity navigation buttons
            activity_button_texts = [
                "Show all posts",
                "Show all comments",
                "Posts",
                "Comments",
            ]

            button_clicked = False
            for button_text in activity_button_texts:
                try:
                    # Find button by text content
                    xpath = f"//button[contains(text(), '{button_text}')]"
                    buttons = self.driver.find_elements(By.XPATH, xpath)

                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            self.logger.info(f"🔘 Clicking '{button_text}' button...")
                            button.click()
                            button_clicked = True
                            time.sleep(3)
                            break

                    if button_clicked:
                        break

                except Exception as e:
                    continue

            # Scroll to load more content
            for i in range(5):
                self.driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )
                time.sleep(2)

            # Extract posts
            post_selectors = [
                ".update-components-text.relative.update-components-update-v2__commentary span[dir='ltr']",
                ".update-components-text span[dir='ltr']",
                ".feed-shared-update-v2 .update-components-text",
                ".feed-shared-update .update-components-text",
            ]

            posts_found = 0
            for selector in post_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)

                    for i, element in enumerate(elements):
                        try:
                            post_text = element.get_attribute("innerHTML")
                            if not post_text:
                                post_text = element.text

                            post_text = re.sub(r"<[^>]+>", "", post_text)
                            post_text = post_text.strip()

                            if post_text and len(post_text) > 10:
                                post_data = {
                                    "index": posts_found + 1,
                                    "text": post_text[:2000],
                                    "extracted_at": datetime.now().isoformat(),
                                }

                                activity_data["posts"].append(post_data)
                                posts_found += 1

                        except Exception as e:
                            continue

                    if posts_found > 0:
                        break

                except Exception as e:
                    continue

            self.logger.info(f"📝 Found {posts_found} posts")
            self.stats["posts_found"] += posts_found

            # Save activity data
            activity_path = output_folder / "enhanced_activity.json"
            with open(activity_path, "w", encoding="utf-8") as f:
                json.dump(activity_data, f, indent=2, ensure_ascii=False)

            total_content = len(activity_data["posts"]) + len(activity_data["comments"])
            self.logger.info(f"✅ Enhanced activity saved: {total_content} items total")

            return True

        except Exception as e:
            self.logger.error(f"❌ Error in enhanced activity scraping: {e}")
            return False

    """
LinkedIn Enhanced Scraper - COMPLETELY FIXED VERSION
PART 6 of 6: Main Scraping Engine, Statistics, and Script Execution
"""

    def scrape_profiles_with_coordinates(
        self, max_pages=5, max_profiles=50, delay_between_profiles=5
    ):
        """Enhanced coordinate-based scraping - COMPLETELY FIXED with reliable contact extraction"""
        try:
            # Load any saved state
            self._load_page_state()

            self.logger.info(
                f"🔍 Starting FIXED coordinate-based scraping from page {self.current_page}..."
            )
            self.logger.info(
                f"🎯 Target: {max_profiles} profile(s) from {max_pages} page(s)"
            )

            # Get browser window dimensions
            window_size = self.driver.get_window_size()
            browser_width = window_size["width"]
            browser_height = window_size["height"]

            self.logger.info(
                f"🖥️ Browser window size: {browser_width}x{browser_height}"
            )

            base_x = browser_width // 2

            # Profile coordinates - ONLY FIRST PROFILE when max_profiles=1
            top_profiles = [
                (base_x, int(browser_height * 0.20), "Profile 1", "20% from top"),
                (base_x, int(browser_height * 0.33), "Profile 2", "33% from top"),
                (base_x, int(browser_height * 0.46), "Profile 3", "46% from top"),
                (base_x, int(browser_height * 0.55), "Profile 4", "55% from top"),
                (base_x, int(browser_height * 0.64), "Profile 5", "64% from top"),
                (base_x, int(browser_height * 0.73), "Profile 6", "73% from top"),
                (base_x, int(browser_height * 0.82), "Profile 7", "82% from top"),
            ]

            # Global tracking
            total_successful_scrapes = 0
            total_profiles_attempted = 0

            # Process each page starting from current page
            while (
                self.current_page <= max_pages
                and total_successful_scrapes < max_profiles
            ):
                try:
                    print(f"\n" + "=" * 70)
                    print(
                        f"📄 PAGE {self.current_page}/{max_pages} - TARGET: {max_profiles} PROFILE(S)"
                    )
                    print(
                        f"👤 Existing users: {len(self.existing_users)}, URLs processed: {len(self.processed_urls)}"
                    )
                    print(
                        f"📞 Contact attempts: {self.stats['contact_info_attempts']}, retries: {self.stats['contact_info_retries']}"
                    )
                    print("=" * 70)

                    page_successful_scrapes = 0
                    page_profiles_attempted = 0

                    # Navigate to current page if not already there
                    current_state = self._check_current_state()
                    if current_state != "search":
                        self.logger.warning(
                            f"⚠️ Not on search page - recovering to page {self.current_page}"
                        )
                        if not self._recover_to_specific_page(self.current_page):
                            self.logger.error(
                                f"❌ Could not recover to page {self.current_page}"
                            )
                            break

                    # Update page tracking
                    self.stats["search_pages"] += 1
                    self.last_successful_page = self.current_page
                    self._save_page_state()

                    # FIXED: Only process profiles up to max_profiles limit
                    if max_profiles == 1:
                        profiles_to_process = 1
                    else:
                        profiles_to_process = min(
                            len(top_profiles), max_profiles - total_successful_scrapes
                        )

                    self.logger.info(
                        f"🎯 Will attempt {profiles_to_process} profile(s) on this page"
                    )

                    for profile_num in range(1, profiles_to_process + 1):
                        # Check if we've reached max profiles
                        if total_successful_scrapes >= max_profiles:
                            print(
                                f"🎯 Reached maximum of {max_profiles} profiles - stopping"
                            )
                            break

                        x, y, description, strategy = top_profiles[profile_num - 1]

                        try:
                            page_profiles_attempted += 1
                            total_profiles_attempted += 1
                            self.stats["total_processed"] += 1

                            print(
                                f"\n🧪 PAGE {self.current_page} - ATTEMPT {profile_num}/{profiles_to_process}: {description.upper()}"
                            )
                            print(f"🎯 Target: {description}")
                            print(f"📐 Coordinates: ({x}, {y})")
                            print(f"📏 Strategy: {strategy}")

                            # Pre-click safety check
                            current_state = self._check_current_state()
                            if current_state != "search":
                                self.logger.warning(
                                    f"⚠️ Not on search page before click - recovering..."
                                )
                                if not self._recover_to_specific_page(
                                    self.current_page
                                ):
                                    print(
                                        f"❌ Could not recover to search page - skipping {description}"
                                    )
                                    continue

                            # Perform the click - scroll to top and click
                            self.logger.info("📜 Ensuring top position...")
                            self.driver.execute_script("window.scrollTo(0, 0);")
                            time.sleep(1)
                            click_success = self._coordinate_click(
                                x, y, f"- {description}"
                            )

                            # Check result with timeout
                            if click_success:
                                self.logger.info(
                                    f"🕐 Waiting 5 seconds to check result..."
                                )
                                time.sleep(5)

                                current_state = self._check_current_state()
                                current_url = self.driver.current_url

                                if current_state == "profile":
                                    # Quick name extraction for duplicate check
                                    profile_name = self._extract_name_quickly()
                                    normalized_profile_name = self._normalize_name(
                                        profile_name
                                    )

                                    # DEBUG: Log the comparison
                                    self.logger.debug(
                                        f"🔍 Checking profile: '{profile_name}' -> normalized: '{normalized_profile_name}'"
                                    )

                                    # Check for existing user FIRST
                                    if normalized_profile_name in self.existing_users:
                                        print(
                                            f"⚠️ {description.upper()} - USER EXISTS! Skipping: {profile_name}"
                                        )
                                        self.stats["skipped_existing"] += 1

                                    # Check for duplicate URL SECOND
                                    elif current_url in self.processed_urls:
                                        print(
                                            f"⚠️ {description.upper()} - DUPLICATE URL! Already processed"
                                        )
                                        self.stats["duplicates_skipped"] += 1

                                    else:
                                        # NEW USER AND NEW URL - proceed with scraping
                                        self.processed_urls.add(current_url)
                                        self.stats["coordinate_clicks_successful"] += 1
                                        print(
                                            f"✅ {description.upper()} SUCCESS! New user: {profile_name}"
                                        )

                                        # COMPREHENSIVE DATA EXTRACTION WITH RELIABLE CONTACT INFO
                                        scrape_result = self.scrape_current_profile()

                                        if scrape_result:
                                            page_successful_scrapes += 1
                                            total_successful_scrapes += 1

                                            # Add to existing users to prevent future duplicates
                                            self.existing_users.add(
                                                normalized_profile_name
                                            )

                                            print(
                                                f"📊 Profile fully scraped! Total: {total_successful_scrapes}/{max_profiles}"
                                            )

                                            # FIXED: Break if we've reached the target
                                            if total_successful_scrapes >= max_profiles:
                                                print(
                                                    f"🎯 TARGET REACHED: {max_profiles} profile(s) completed!"
                                                )
                                                break
                                        else:
                                            print(
                                                f"⚠️ Profile scraping failed for {description}"
                                            )

                                    # Go back to search page
                                    self.logger.info(
                                        f"⬅️ Going back from {description}..."
                                    )
                                    if not self._recover_to_specific_page(
                                        self.current_page
                                    ):
                                        self.logger.warning(
                                            "⚠️ Could not return to search page"
                                        )
                                    # FIXED: Check if we've reached target AFTER going back
                                    if total_successful_scrapes >= max_profiles:
                                        print(
                                            f"🎯 REACHED TARGET: {max_profiles} profile(s) completed!"
                                        )
                                        break

                                elif current_state == "search":
                                    # FAILED - still on search page, click didn't work
                                    print(
                                        f"⚠️ {description.upper()} FAILED - Click didn't navigate anywhere"
                                    )
                                    self.stats["coordinate_clicks_failed"] += 1

                                else:
                                    # UNKNOWN - somewhere else, recover
                                    print(
                                        f"⚠️ {description.upper()} UNKNOWN STATE - Recovering to search"
                                    )
                                    self._recover_to_specific_page(self.current_page)
                                    self.stats["coordinate_clicks_failed"] += 1
                            else:
                                print(f"❌ {description.upper()} CLICK FAILED")
                                self.stats["coordinate_clicks_failed"] += 1

                            # Save state after each profile
                            self._save_page_state()

                            # FIXED: Check if target reached before delay
                            if total_successful_scrapes >= max_profiles:
                                break

                            # Delay between profiles
                            if profile_num < profiles_to_process:
                                time.sleep(delay_between_profiles)

                        except KeyboardInterrupt:
                            print(
                                f"\n⚠️ Scraping interrupted at Page {self.current_page}, {description}"
                            )
                            self._save_page_state()
                            return False
                        except Exception as e:
                            self.logger.error(
                                f"❌ Error with Page {self.current_page}, {description}: {e}"
                            )
                            print(f"❌ Error with {description}: {e}")
                            continue

                    # FIXED: Break if we've reached our target
                    if total_successful_scrapes >= max_profiles:
                        print(
                            f"\n🎯 TARGET COMPLETED: {max_profiles} profile(s) successfully scraped!"
                        )
                        break

                    # Page summary with enhanced contact info stats
                    page_success_rate = (
                        (page_successful_scrapes / profiles_to_process) * 100
                        if page_profiles_attempted > 0
                        else 0
                    )
                    contact_success_rate = (
                        self.stats["contact_info_found"]
                        / max(1, self.stats["contact_info_attempts"])
                    ) * 100

                    print(f"\n📊 PAGE {self.current_page} SUMMARY:")
                    print(f"🎯 Profiles Attempted: {page_profiles_attempted}")
                    print(f"✅ Successful Scrapes: {page_successful_scrapes}")
                    print(f"⚠️ Skipped Existing: {self.stats['skipped_existing']}")
                    print(
                        f"❌ Failed Attempts: {page_profiles_attempted - page_successful_scrapes}"
                    )
                    print(f"📈 Page Success Rate: {page_success_rate:.1f}%")
                    print(
                        f"📞 Contact Info Success: {contact_success_rate:.1f}% ({self.stats['contact_info_found']}/{self.stats['contact_info_attempts']})"
                    )

                    # Only move to next page if we haven't reached our target
                    if (
                        total_successful_scrapes < max_profiles
                        and self.current_page < max_pages
                    ):
                        self.current_page += 1
                        continue
                    else:
                        break

                except Exception as e:
                    self.logger.error(
                        f"❌ Error processing page {self.current_page}: {e}"
                    )
                    break

            # Final results with enhanced contact info stats
            overall_success_rate = (
                (total_successful_scrapes / total_profiles_attempted) * 100
                if total_profiles_attempted > 0
                else 0
            )
            contact_overall_rate = (
                self.stats["contact_info_found"]
                / max(1, self.stats["contact_info_attempts"])
            ) * 100

            print(f"\n" + "=" * 80)
            print(f"🎉 COMPLETELY FIXED SCRAPING WITH RELIABLE CONTACT INFO COMPLETE!")
            print(f"📊 FINAL STATS:")
            print(f"🎯 Target: {max_profiles} profile(s)")
            print(
                f"✅ Successfully Completed: {total_successful_scrapes}/{max_profiles}"
            )
            print(f"📄 Pages Processed: {self.current_page}")
            print(f"🎯 Total Profiles Attempted: {total_profiles_attempted}")
            print(f"⚠️ Skipped Existing Users: {self.stats['skipped_existing']}")
            print(
                f"❌ Total Failed Attempts: {total_profiles_attempted - total_successful_scrapes}"
            )
            print(f"📈 Overall Success Rate: {overall_success_rate:.1f}%")
            print("")
            print(f"📞 RELIABLE CONTACT INFO EXTRACTION STATS:")
            print(f"📞 Contact Attempts: {self.stats['contact_info_attempts']}")
            print(f"🔄 Contact Retries: {self.stats['contact_info_retries']}")
            print(f"✅ Contact Info Found: {self.stats['contact_info_found']}")
            print(f"📧 Emails Found: {self.stats['emails_found']}")
            print(f"📱 Phones Found: {self.stats['phones_found']}")
            print(f"🌐 Websites Found: {self.stats['websites_found']}")
            print(f"📈 Contact Success Rate: {contact_overall_rate:.1f}%")
            print("")
            print(f"📁 Output Directory: {self.output_dir}")
            print("=" * 80)

            return True

        except Exception as e:
            self.logger.error(
                f"❌ Error in COMPLETELY FIXED coordinate-based scraping: {e}"
            )
            self._save_page_state()
            return False

    def close(self):
        """Close browser and save final state"""
        if hasattr(self, "driver"):
            self.logger.info("🔒 Closing browser...")
            self._save_page_state()
            self.driver.quit()


def main():
    """Main function"""

    # Configuration - COMPLETELY FIXED VALUES
    MAX_PAGES = 50  # Search pages to scrape (1-50)
    MAX_PROFILES = 500  # Total profiles to process (1-500)
    DELAY_BETWEEN_PROFILES = 5  # Seconds between profiles (3-10)

    print("🚀 LinkedIn Enhanced Safe Scraper Starting - COMPLETELY FIXED VERSION...")
    print(f"🎯 Target: {MAX_PROFILES} profiles from {MAX_PAGES} pages")
    print("✨ Features: RELIABLE contact extraction using tested CSS selectors")
    print("📞 NEW: LinkedIn URL filtering + robust error handling")

    scraper = LinkedInEnhancedScraper(
        output_dir="linkedin_enhanced_scrape_authors", headless=False
    )

    try:
        # Login
        if not scraper.wait_for_manual_login():
            print("❌ Login failed")
            return

        # Setup search with manual filters
        if not scraper.setup_manual_search_filters():
            print("❌ Search setup failed")
            return

        # Scrape profiles using COMPLETELY FIXED coordinate-based clicking with reliable contact extraction
        success = scraper.scrape_profiles_with_coordinates(
            max_pages=MAX_PAGES,
            max_profiles=MAX_PROFILES,
            delay_between_profiles=DELAY_BETWEEN_PROFILES,
        )

        if success:
            print(
                "\n✅ COMPLETELY FIXED SCRAPING WITH RELIABLE CONTACT INFO COMPLETED SUCCESSFULLY!"
            )
            print(
                "📞 Check the detailed contact info stats above - should show clean extracted data!"
            )
        else:
            print("\n❌ SCRAPING FAILED")

        input("\n⏳ Press Enter to close browser...")

    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
