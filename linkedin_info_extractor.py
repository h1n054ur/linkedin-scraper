#!/usr/bin/env python3
"""
LinkedIn Info Extractor - Production Version
Processes profile URLs from URL collector and extracts comprehensive profile data
Creates unified {Name}_info.json with profile data, contact info, and all activities
"""

import time
import re
import json
import os
import shutil
import requests
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service

class ProductionInfoExtractor:
    def __init__(self, output_dir="scraped_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # URL Collector paths
        self.url_collector_dir = Path("./linkedin_url_collector")
        self.profile_links_file = self.url_collector_dir / "profile_links.json"
        self.cookies_file = self.url_collector_dir / "cookies.json"
        
        # WSL Downloads directory
        self.downloads_dir = Path.home() / "Downloads"
        
        # Get next folder number
        self.next_folder_number = self._get_next_folder_number()
        
        # Processing stats
        self.stats = {
            'total_profiles': 0,
            'processed_profiles': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'start_time': datetime.now()
        }
        
    def check_cookies(self):
        """Check if cookies file exists and is valid"""
        try:
            if not self.cookies_file.exists():
                print("❌ No cookies file found")
                return False
                
            with open(self.cookies_file, 'r') as f:
                cookie_data = json.load(f)
                
            if 'cookies' in cookie_data and 'user_agent' in cookie_data:
                timestamp = cookie_data.get('timestamp')
                if timestamp:
                    cookie_time = datetime.fromisoformat(timestamp)
                    age_days = (datetime.now() - cookie_time).days
                    print(f"✅ Found valid cookies from {age_days} days ago")
                return True
            else:
                print("❌ Cookies file invalid")
                return False
                
        except Exception as e:
            print(f"❌ Error checking cookies: {e}")
            return False
            
    def setup_manual_cookies(self):
        """Manual login to collect cookies"""
        print("\n" + "="*80)
        print("🔧 MANUAL COOKIE COLLECTION")
        print("="*80)
        
        # Setup visible browser for login
        options = ChromeOptions()
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        service = Service("./chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        try:
            print("🌐 Opening LinkedIn for login...")
            driver.get("https://www.linkedin.com")
            time.sleep(2)
            
            print("\n" + "="*60)
            print("⏳ PLEASE LOG IN TO LINKEDIN")
            print("="*60)
            print("🔐 1. Complete LinkedIn login")
            print("✅ 2. Press ENTER when logged in and ready...")
            input()
            
            # Extract cookies
            print("🍪 Extracting cookies...")
            cookies = driver.get_cookies()
            
            # Ensure URL collector directory exists
            self.url_collector_dir.mkdir(exist_ok=True)
            
            cookie_data = {
                'cookies': cookies,
                'timestamp': datetime.now().isoformat(),
                'user_agent': driver.execute_script("return navigator.userAgent;")
            }
            
            with open(self.cookies_file, 'w') as f:
                json.dump(cookie_data, f, indent=2)
                
            print(f"✅ Cookies saved to {self.cookies_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error in manual cookie setup: {e}")
            return False
        finally:
            driver.quit()
            print("🔒 Browser closed")
            
    def setup_headless_browser(self):
        """Setup headless browser with cookies"""
        try:
            if not self.cookies_file.exists():
                raise Exception("Cookies file not found")
                
            with open(self.cookies_file, 'r') as f:
                cookie_data = json.load(f)
                
            # Setup headless browser
            options = ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            options.add_argument(f'--user-agent={cookie_data.get("user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")}')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Downloads preferences
            prefs = {
                "download.default_directory": str(self.downloads_dir),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "plugins.always_open_pdf_externally": True,
                "safebrowsing.enabled": True,
            }
            options.add_experimental_option("prefs", prefs)
            
            service = Service("./chromedriver")
            driver = webdriver.Chrome(service=service, options=options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Navigate to LinkedIn first
            driver.get("https://www.linkedin.com")
            time.sleep(1)
            
            # Add cookies
            for cookie in cookie_data['cookies']:
                try:
                    driver.add_cookie(cookie)
                except Exception:
                    continue
                    
            return driver
            
        except Exception as e:
            print(f"❌ Error setting up headless browser: {e}")
            return None
            
    def setup_requests_session(self, driver):
        """Setup requests session with cookies from browser"""
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })
        
        # Sync cookies from browser
        session.cookies.clear()
        for cookie in driver.get_cookies():
            session.cookies.set(
                cookie["name"],
                cookie["value"],
                domain=cookie.get("domain", ".linkedin.com"),
            )
            
        return session

    def _get_next_folder_number(self):
        """Find the highest existing folder number and return the next one"""
        try:
            existing_folders = [d for d in self.output_dir.iterdir() if d.is_dir()]
            max_number = 0

            for folder in existing_folders:
                folder_name = folder.name
                if "_" in folder_name:
                    first_part = folder_name.split("_")[0]
                    if first_part.isdigit():
                        number = int(first_part)
                        max_number = max(max_number, number)

            next_number = max_number + 1
            print(f"📊 Starting folder number: {next_number}")
            return next_number

        except Exception as e:
            print(f"❌ Error getting next folder number: {e}")
            return 1

    def _clean_filename(self, name):
        """Clean name for safe folder/filename"""
        clean = re.sub(r'[<>:"/\\|?*]', "_", name.strip())
        clean = re.sub(r"[^\w\s-]", "", clean)
        clean = re.sub(r"\s+", "_", clean)
        return clean[:50]

    def _extract_profile_info(self, driver, profile_url):
        """Extract comprehensive profile information"""
        try:
            print("👤 Extracting profile information...")
            
            profile_info = {
                "name": "Unknown",
                "clean_filename": "Unknown",
                "profile_url": profile_url,
                "title": None,
                "location": None,
                "connection_degree": None,
                "verified": False,
                "premium": False,
                "follower_count": None,
                "extracted_at": datetime.now().isoformat(),
                "profile_picture_url": None,
                "extraction_metadata": {
                    "contact_button_found": False,
                    "modal_opened": False,
                    "profile_picture_downloaded": False,
                    "pdf_downloaded": False,
                    "activity_extracted": False
                }
            }
            
            # Extract name
            name_selectors = [
                "h1.text-heading-xlarge",
                "h1",
                ".pv-text-details__left-panel h1",
                ".update-components-actor__title span[aria-hidden='true']"
            ]

            for selector in name_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    name = element.text.strip()
                    if name and len(name) > 2:
                        profile_info["name"] = name
                        profile_info["clean_filename"] = self._clean_filename(name)
                        break
                except:
                    continue
            
            # Extract title/headline
            title_selectors = [
                ".text-body-medium.break-words",
                ".pv-text-details__left-panel .text-body-medium",
                ".update-components-actor__description"
            ]
            
            for selector in title_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    title = element.text.strip()
                    if title and len(title) > 5:
                        profile_info["title"] = title
                        break
                except:
                    continue
            
            # Extract profile picture URL
            img_selectors = [
                "img.pv-top-card-profile-picture__image--show",
                "img.evi-image",
                "img[alt*='profile']",
                ".update-components-actor__avatar img"
            ]

            for selector in img_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    if element.is_displayed():
                        src = element.get_attribute("src")
                        if src and ("profile" in src or "displayphoto" in src):
                            profile_info["profile_picture_url"] = src
                            break
                except:
                    continue
            
            # Check for verification/premium badges
            try:
                verified_elements = driver.find_elements(By.CSS_SELECTOR, 
                    "svg[data-test-icon='verified-small'], .text-view-model__verified-icon")
                if verified_elements:
                    profile_info["verified"] = True
                    
                premium_elements = driver.find_elements(By.CSS_SELECTOR,
                    "svg[data-test-icon*='premium'], .text-view-model__linkedin-bug-premium")
                if premium_elements:
                    profile_info["premium"] = True
            except:
                pass
                
            print(f"👤 Profile Info: {profile_info['name']} - {profile_info['title']}")
            return profile_info

        except Exception as e:
            print(f"❌ Error extracting profile info: {e}")
            return None
        
    def _is_valid_email(self, email):
        """Validate email format"""
        try:
            if not email or len(email) < 5:
                return False
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return re.match(pattern, email) is not None
        except:
            return False
        
    def _is_valid_phone(self, phone):
        """Validate phone number format"""
        try:
            if not phone:
                return False
            clean_phone = re.sub(r'[^\d+\-\(\)\s]', '', phone)
            digits = re.findall(r'\d', clean_phone)
            return len(digits) >= 7
        except:
            return False
        
    def _is_valid_website(self, url):
        """Validate website URL format"""
        try:
            if not url or len(url) < 10:
                return False
            if not url.lower().startswith(('http://', 'https://')):
                return False
            if '.' not in url:
                return False
            
            skip_patterns = [
                'mailto:', 
                'tel:', 
                'javascript:', 
                'linkedin.com/',
                'www.linkedin.com/'
            ]
            
            for pattern in skip_patterns:
                if pattern in url.lower():
                    return False
            return True
        except Exception:
            return False
    
    def find_contact_button(self, driver):
        """Find contact info button"""
        contact_selectors = [
            {
                'name': 'CSS ID',
                'method': By.CSS_SELECTOR,
                'selector': '#top-card-text-details-contact-info'
            },
            {
                'name': 'CSS Class',
                'method': By.CSS_SELECTOR,
                'selector': 'a.link-without-visited-state'
            },
            {
                'name': 'CSS Href', 
                'method': By.CSS_SELECTOR,
                'selector': 'a[href*="contact-info"]'
            }
        ]
        
        for selector_info in contact_selectors:
            try:
                print(f"🔍 Trying: {selector_info['name']}")
                
                elements = driver.find_elements(selector_info['method'], selector_info['selector'])
                
                for element in elements:
                    try:
                        if element.is_displayed() and element.is_enabled():
                            print(f"✅ Found contact button: {selector_info['name']}")
                            return element, selector_info['name']
                    except Exception:
                        continue
                        
            except Exception as e:
                print(f"❌ Selector failed: {e}")
                continue
        
        return None, None
    
    def extract_contact_info_from_modal(self, driver):
        """Extract contact information from modal"""
        contact_data = {
            'email': None,
            'phone': None,
            'websites': [],
            'extraction_details': {}
        }
        
        print("📞 Extracting contact information...")
        time.sleep(3)
        
        # EMAIL EXTRACTION
        email_selectors = [
            "a[href*='mailto:']",
            "section div a[href*='mailto']", 
            "section:nth-child(4) div a",
            "section:last-child div a"
        ]
        
        for i, selector in enumerate(email_selectors):
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    href = element.get_attribute('href')
                    text = element.text.strip()
                    
                    if href and 'mailto:' in href:
                        email = href.replace('mailto:', '').strip()
                        if self._is_valid_email(email):
                            contact_data['email'] = email
                            print(f"📧 EMAIL FOUND: {email}")
                            break
                    elif text and '@' in text and self._is_valid_email(text):
                        contact_data['email'] = text
                        print(f"📧 EMAIL FOUND: {text}")
                        break
                        
                if contact_data['email']:
                    break
            except Exception:
                continue
        
        # PHONE EXTRACTION
        phone_selectors = [
            "a[href*='tel:']",
            "section:nth-child(3) ul li span",
            "section:nth-child(3) ul li", 
            "section div ul li span"
        ]
        
        for i, selector in enumerate(phone_selectors):
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    href = element.get_attribute('href')
                    text = element.text.strip()
                    
                    if href and 'tel:' in href:
                        phone = href.replace('tel:', '').strip()
                        if self._is_valid_phone(phone):
                            contact_data['phone'] = phone
                            print(f"📱 PHONE FOUND: {phone}")
                            break
                    elif text and self._is_valid_phone(text):
                        contact_data['phone'] = text
                        print(f"📱 PHONE FOUND: {text}")
                        break
                        
                if contact_data['phone']:
                    break
            except Exception:
                continue
        
        # WEBSITE EXTRACTION
        website_selectors = [
            "section:nth-child(2) ul li a",
            "section:nth-child(2) div a",
            "section div ul li a",
            "a[href^='http']"
        ]
        
        for selector in website_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    href = element.get_attribute('href')
                    text = element.text.strip()
                    
                    if href and self._is_valid_website(href):
                        website_data = {
                            'url': href,
                            'display_text': text if text else href
                        }
                        
                        if not any(w['url'] == href for w in contact_data['websites']):
                            contact_data['websites'].append(website_data)
                            print(f"🌐 WEBSITE FOUND: {href}")
                            
            except Exception:
                continue
        
        return contact_data
    
    def close_contact_modal(self, driver):
        """Close the contact modal"""
        try:
            print("🔄 Closing contact modal...")
            
            close_methods = [
                "button[aria-label*='Dismiss']",
                "button[aria-label*='Close']", 
                ".artdeco-modal__dismiss",
                "button.artdeco-button--circle"
            ]
            
            modal_closed = False
            for selector in close_methods:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            element.click()
                            modal_closed = True
                            print("✅ Modal closed")
                            break
                    if modal_closed:
                        break
                except Exception:
                    continue
            
            if not modal_closed:
                actions = ActionChains(driver)
                actions.send_keys(Keys.ESCAPE)
                actions.perform()
                print("✅ Modal closed with ESC")
            
            time.sleep(2)
            return True
            
        except Exception as e:
            print(f"❌ Error closing modal: {e}")
            return False

    def download_profile_picture(self, driver, session, person_folder):
        """Download profile picture"""
        try:
            print("🖼️ Downloading profile picture...")

            img_selectors = [
                "img.pv-top-card-profile-picture__image--show",
                "img.evi-image",
                "img[alt*='profile']",
            ]

            img_url = None
            for selector in img_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
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
                print("⚠️ No profile picture found")
                return False

            response = session.get(img_url, timeout=30)
            response.raise_for_status()

            ext = ".jpg" if "jpg" in response.headers.get("content-type", "") else ".png"
            img_path = person_folder / f"profile_picture{ext}"

            with open(img_path, "wb") as f:
                f.write(response.content)

            print(f"✅ Profile picture saved")
            return True

        except Exception as e:
            print(f"❌ Profile picture error: {e}")
            return False

    def _move_downloaded_pdf(self, person_folder):
        """Move downloaded PDF"""
        try:
            pdf_patterns = [
                self.downloads_dir / "Profile.pdf",
                list(self.downloads_dir.glob("Profile*.pdf")),
                list(self.downloads_dir.glob("*.pdf"))
            ]

            downloaded_pdf = None
            for pattern in pdf_patterns:
                if isinstance(pattern, Path) and pattern.exists():
                    downloaded_pdf = pattern
                    break
                elif isinstance(pattern, list) and pattern:
                    downloaded_pdf = max(pattern, key=os.path.getctime)
                    break

            if downloaded_pdf and downloaded_pdf.exists():
                destination = person_folder / "profile.pdf"
                shutil.move(str(downloaded_pdf), str(destination))
                print("✅ PDF moved")
                return True
            else:
                print("⚠️ No PDF found")
                return False

        except Exception as e:
            print(f"❌ Error moving PDF: {e}")
            return False

    def download_profile_pdf(self, driver, person_folder):
        """Download profile PDF"""
        try:
            print("📄 Downloading PDF...")

            # Clear old PDFs
            for pdf in self.downloads_dir.glob("Profile*.pdf"):
                try:
                    pdf.unlink()
                except:
                    pass

            more_selectors = [
                "button[aria-label*='More actions']",
                "button[id*='profile-overflow-action']",
            ]

            more_button = None
            for selector in more_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            more_button = element
                            break
                    if more_button:
                        break
                except:
                    continue

            if more_button:
                print("🔘 Clicking More actions...")
                more_button.click()
                time.sleep(2)

                pdf_selectors = [
                    "div[role='menuitem']",
                    "button[role='menuitem']",
                    ".artdeco-dropdown__item",
                ]

                for selector in pdf_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if element.is_displayed() and "PDF" in element.text:
                                print("📄 Clicking PDF option...")
                                element.click()
                                time.sleep(5)
                                return self._move_downloaded_pdf(person_folder)
                    except:
                        continue

            return False

        except Exception as e:
            print(f"❌ PDF download error: {e}")
            return False

    def infinite_scroll_and_extract(self, driver, url, content_type="posts"):
        """Extract content with infinite scroll"""
        try:
            print(f"🔄 Extracting {content_type}...")
            driver.get(url)
            time.sleep(5)
            
            if content_type == "posts":
                content_selectors = [
                    ".update-components-text.relative.update-components-update-v2__commentary span[dir='ltr']",
                    ".feed-shared-update-v2__description .update-components-text span[dir='ltr']",
                    ".update-components-text span[dir='ltr']"
                ]
            else:  # comments
                content_selectors = [
                    ".comments-comment-item__main-content .update-components-text span[dir='ltr']",
                    ".comments-comment-entity__content .update-components-text span[dir='ltr']",
                    ".comments-comment-item__main-content"
                ]
            
            extracted_content = []
            max_scrolls = 20
            iteration_count = 0
            previous_content_count = 0
            no_new_content_count = 0
            
            while iteration_count < max_scrolls:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                
                current_elements = []
                for selector in content_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        current_elements.extend(elements)
                    except Exception:
                        continue
                
                current_count = len(current_elements)
                
                if current_count == previous_content_count:
                    no_new_content_count += 1
                    if no_new_content_count >= 3:
                        break
                else:
                    no_new_content_count = 0
                
                previous_content_count = current_count
                iteration_count += 1
            
            # Extract final content
            for selector in content_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        try:
                            content_text = element.get_attribute("innerHTML")
                            if not content_text:
                                content_text = element.text
                            
                            content_text = re.sub(r"<[^>]+>", "", content_text)
                            content_text = content_text.strip()
                            
                            if content_text and len(content_text) > 10:
                                content_item = {
                                    "index": len(extracted_content) + 1,
                                    "type": "original_post" if content_type == "posts" else "comment",
                                    "content": content_text[:2000],
                                    "timestamp": None,
                                    "extracted_at": datetime.now().isoformat()
                                }
                                
                                if not any(item['content'] == content_text[:2000] for item in extracted_content):
                                    extracted_content.append(content_item)
                                    
                        except Exception:
                            continue
                    
                    if extracted_content:
                        break
                        
                except Exception:
                    continue
            
            print(f"✅ Extracted {len(extracted_content)} {content_type}")
            return extracted_content
            
        except Exception as e:
            print(f"❌ Error extracting {content_type}: {e}")
            return []

    def create_unified_profile_data(self, profile_info, contact_data, posts, comments):
        """Create unified profile JSON"""
        try:
            activity_summary = {
                "total_posts": len(posts),
                "total_comments": len(comments),
                "total_activities": len(posts) + len(comments)
            }
            
            unified_data = {
                "profile_info": profile_info,
                "contact_info": contact_data,
                "activity_summary": activity_summary,
                "posts": posts,
                "comments": comments,
                "extraction_log": {
                    "script_version": "3.0.0-production",
                    "extraction_completed_at": datetime.now().isoformat()
                }
            }
            
            return unified_data
            
        except Exception as e:
            print(f"❌ Error creating unified data: {e}")
            return None

    def process_single_profile(self, profile_url, profile_name):
        """Process a single profile completely"""
        print(f"\n" + "="*80)
        print(f"🎯 PROCESSING: {profile_name}")
        print(f"🌐 URL: {profile_url}")
        print("="*80)
        
        # Start fresh browser for this profile
        driver = self.setup_headless_browser()
        if not driver:
            print("❌ Failed to setup browser")
            return False
        
        session = self.setup_requests_session(driver)
        
        try:
            # Navigate to profile
            print(f"🌐 Navigating to profile...")
            driver.get(profile_url)
            time.sleep(5)
            
            # Extract profile info
            profile_info = self._extract_profile_info(driver, profile_url)
            if not profile_info:
                print("❌ Failed to extract profile info")
                return False
            
            # Create folder
            clean_name = self._clean_filename(f"{self.next_folder_number}_{profile_info['clean_filename']}")
            person_folder = self.output_dir / clean_name
            person_folder.mkdir(exist_ok=True)
            print(f"📁 Created folder: {clean_name}")
            self.next_folder_number += 1
            
            # Initialize contact data
            contact_data = {
                'email': None,
                'phone': None,
                'websites': [],
                'extraction_details': {}
            }
            
            # Extract contact info
            print("📞 Extracting contact information...")
            contact_button, button_method = self.find_contact_button(driver)
            
            if contact_button:
                try:
                    print(f"🔘 Clicking contact button...")
                    contact_button.click()
                    time.sleep(5)
                    
                    # Check if modal opened
                    modal_indicators = [
                        'div[role="dialog"]',
                        '.artdeco-modal',
                        '.pv-contact-info'
                    ]
                    
                    modal_found = False
                    for indicator in modal_indicators:
                        try:
                            modal_elements = driver.find_elements(By.CSS_SELECTOR, indicator)
                            if any(elem.is_displayed() for elem in modal_elements):
                                modal_found = True
                                print("✅ Modal opened")
                                break
                        except:
                            continue
                    
                    if modal_found:
                        contact_data = self.extract_contact_info_from_modal(driver)
                        profile_info['extraction_metadata']['modal_opened'] = True
                        self.close_contact_modal(driver)
                    else:
                        print("❌ Modal did not open")
                        
                except Exception as e:
                    print(f"❌ Error during contact extraction: {e}")
                    self.close_contact_modal(driver)
            else:
                print("❌ No contact button found")
            
            # Download profile picture
            print("🖼️ Downloading profile picture...")
            picture_success = self.download_profile_picture(driver, session, person_folder)
            profile_info['extraction_metadata']['profile_picture_downloaded'] = picture_success

            # Download PDF
            print("📄 Downloading PDF...")
            pdf_success = self.download_profile_pdf(driver, person_folder)
            profile_info['extraction_metadata']['pdf_downloaded'] = pdf_success

            # Extract Posts
            print("📝 Extracting posts...")
            posts_url = f"{profile_url.rstrip('/')}/recent-activity/all/"
            posts = self.infinite_scroll_and_extract(driver, posts_url, "posts")
            
            # Extract Comments  
            print("💬 Extracting comments...")
            comments_url = f"{profile_url.rstrip('/')}/recent-activity/comments/"
            comments = self.infinite_scroll_and_extract(driver, comments_url, "comments")
            
            # Mark activity as extracted if we got any content
            if posts or comments:
                profile_info['extraction_metadata']['activity_extracted'] = True

            # Create Unified JSON
            print("📋 Creating unified JSON...")
            unified_data = self.create_unified_profile_data(
                profile_info, contact_data, posts, comments
            )
            
            if unified_data:
                json_filename = f"{profile_info['clean_filename']}_info.json"
                json_path = person_folder / json_filename
                
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(unified_data, f, indent=2, ensure_ascii=False)
                
                print(f"✅ Unified JSON saved: {json_filename}")
            else:
                print("❌ Failed to create unified JSON")

            # Summary
            print(f"\n📊 PROFILE SUMMARY:")
            print(f"👤 Name: {profile_info['name']}")
            print(f"📁 Folder: {clean_name}")
            print(f"📧 Email: {contact_data['email'] or 'Not found'}")
            print(f"📱 Phone: {contact_data['phone'] or 'Not found'}")
            print(f"🌐 Websites: {len(contact_data['websites'])}")
            print(f"🖼️ Profile Picture: {'✅' if picture_success else '❌'}")
            print(f"📄 PDF: {'✅' if pdf_success else '❌'}")
            print(f"📝 Posts: {len(posts)}")
            print(f"💬 Comments: {len(comments)}")
            
            self.stats['successful_extractions'] += 1
            return True
            
        except Exception as e:
            print(f"❌ Error processing profile: {e}")
            self.stats['failed_extractions'] += 1
            return False
        finally:
            driver.quit()
            print("🔒 Browser closed for this profile")

    def read_profile_links_stream(self):
        """Generator to read profile links one at a time"""
        try:
            if not self.profile_links_file.exists():
                print(f"❌ Profile links file not found: {self.profile_links_file}")
                return
                
            with open(self.profile_links_file, 'r') as f:
                profile_links = json.load(f)
                
            self.stats['total_profiles'] = len(profile_links)
            print(f"📊 Found {self.stats['total_profiles']} profiles to process")
            
            for profile_url, profile_name in profile_links.items():
                yield profile_url, profile_name
                
        except Exception as e:
            print(f"❌ Error reading profile links: {e}")
            return

    def run_production_extraction(self):
        """Main production extraction workflow"""
        print("🚀 LinkedIn Info Extractor - PRODUCTION MODE")
        print("🎯 Automated profile processing with headless browser")
        print("📋 Extracts: contact info + images + PDFs + posts + comments")
        print("="*80)
        
        # Check cookies first
        has_cookies = self.check_cookies()
        
        if not has_cookies:
            print("\n🔧 No valid cookies found - setting up manual login...")
            if not self.setup_manual_cookies():
                print("❌ Cookie setup failed - exiting")
                return False
        
        print("\n✅ Cookies ready - starting automated processing...")
        
        # Process each profile
        for profile_url, profile_name in self.read_profile_links_stream():
            self.stats['processed_profiles'] += 1
            
            print(f"\n🔄 PROGRESS: {self.stats['processed_profiles']}/{self.stats['total_profiles']}")
            
            try:
                self.process_single_profile(profile_url, profile_name)
            except Exception as e:
                print(f"❌ Fatal error processing {profile_name}: {e}")
                self.stats['failed_extractions'] += 1
                continue
            
            # Brief pause between profiles
            print("⏳ Pausing before next profile...")
            time.sleep(2)
        
        # Final statistics
        self.show_final_stats()
        
    def show_final_stats(self):
        """Show final processing statistics"""
        end_time = datetime.now()
        total_time = end_time - self.stats['start_time']
        
        print(f"\n" + "="*80)
        print("🎉 LINKEDIN INFO EXTRACTOR - PRODUCTION COMPLETE")
        print("="*80)
        
        print(f"\n📊 FINAL STATISTICS:")
        print(f"📅 Start Time: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📅 End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️ Total Time: {total_time}")
        print(f"👤 Total Profiles: {self.stats['total_profiles']}")
        print(f"✅ Successful Extractions: {self.stats['successful_extractions']}")
        print(f"❌ Failed Extractions: {self.stats['failed_extractions']}")
        
        if self.stats['total_profiles'] > 0:
            success_rate = (self.stats['successful_extractions'] / self.stats['total_profiles']) * 100
            print(f"📈 Success Rate: {success_rate:.1f}%")
            
            if self.stats['successful_extractions'] > 0:
                avg_time_per_profile = total_time.total_seconds() / self.stats['successful_extractions']
                print(f"⚡ Avg Time per Profile: {avg_time_per_profile:.1f} seconds")
        
        print(f"\n📁 All data saved in: {self.output_dir}")
        print("="*80)


def main():
    """Main function"""
    extractor = ProductionInfoExtractor()
    
    try:
        extractor.run_production_extraction()
    except KeyboardInterrupt:
        print("\n⚠️ Extraction interrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
    finally:
        print("\n✅ Production extraction finished")


if __name__ == "__main__":
    main()