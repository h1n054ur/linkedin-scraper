#!/usr/bin/env python3
"""
LinkedIn Integrated Safe Scraper - Fixed Version
Combines proven coordinate clicking with comprehensive profile scraping including websites
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

class LinkedInIntegratedScraper:
    def __init__(self, output_dir="linkedin_integrated_scrape", headless=False):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.headless = headless
        
        # WSL Downloads directory
        self.downloads_dir = Path.home() / "Downloads"
        
        # Setup verbose logging
        self._setup_logging()
        
        # Setup browser
        self.driver = self._setup_browser()
        self.wait = WebDriverWait(self.driver, 15)
        
        # Setup requests session
        self._setup_requests_session()
        
        # Coordinate clicking variables
        self.processed_urls = set()  # Track processed URLs to avoid duplicates
        
        # Stats tracking
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'search_pages': 0,
            'profiles_found': 0,
            'contact_info_found': 0,
            'emails_found': 0,
            'phones_found': 0,
            'websites_found': 0,
            'posts_found': 0,
            'comments_found': 0,
            'coordinate_clicks_successful': 0,
            'coordinate_clicks_failed': 0,
            'duplicates_skipped': 0
        }
        
    def _setup_logging(self):
        """Setup verbose logging"""
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler = logging.FileHandler(self.output_dir / 'integrated_scraper.log')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info("🚀 LinkedIn Integrated Scraper initialized")
        self.logger.debug(f"📁 Output directory: {self.output_dir}")
        self.logger.debug(f"💾 Downloads directory: {self.downloads_dir}")
        
    def _setup_browser(self):
        """Setup Chrome browser with visible mouse cursor"""
        self.logger.debug("🌐 Setting up Chrome browser...")
        
        options = ChromeOptions()
        
        prefs = {
            "download.default_directory": str(self.downloads_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        
        if self.headless:
            options.add_argument('--headless')
        else:
            self.logger.info("🌐 Starting browser - please log in manually when prompted")
            
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Add CSS to make mouse cursor more visible
        driver.execute_script("""
            var style = document.createElement('style');
            style.innerHTML = '*{cursor: crosshair !important;}';
            document.head.appendChild(style);
        """)
        
        self.logger.debug("✅ Chrome browser setup complete")
        return driver
        
    def _setup_requests_session(self):
        """Setup requests session"""
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })
        
    def _coordinate_click(self, x, y, description="", move_slow=True):
        """Click at specific coordinates with visible mouse movement"""
        try:
            self.logger.info(f"🎯 Moving mouse to coordinates ({x}, {y}) {description}")
            
            # Create visible mouse movement
            actions = ActionChains(self.driver)
            
            if move_slow:
                # Move slowly to make it visible
                actions.move_by_offset(x, y)
                actions.pause(0.5)  # Pause at target location
            else:
                actions.move_by_offset(x, y)
            
            # Click and hold briefly to make it visible
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
            
            if '/in/' in current_url:
                return "profile"
            elif '/search/' in current_url:
                return "search" 
            else:
                return "unknown"
                
        except Exception as e:
            self.logger.error(f"❌ Error checking current state: {e}")
            return "unknown"
            
    def _recover_to_search(self, stored_search_url):
        """Recover to search page using stored URL"""
        try:
            self.logger.warning("🔄 Attempting recovery to search page...")
            
            if stored_search_url:
                self.logger.info(f"🔄 Navigating to stored search URL: {stored_search_url}")
                self.driver.get(stored_search_url)
                time.sleep(3)
                
                # Verify recovery worked
                if self._check_current_state() == "search":
                    self.logger.info("✅ Successfully recovered to search page")
                    return True
                else:
                    self.logger.error("❌ Recovery failed - not on search page")
                    return False
            else:
                self.logger.error("❌ No stored search URL available")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error during recovery: {e}")
            return False
            
    def _sync_cookies(self):
        """Sync cookies from browser to requests session"""
        try:
            self.session.cookies.clear()
            for cookie in self.driver.get_cookies():
                self.session.cookies.set(
                    cookie['name'], 
                    cookie['value'], 
                    domain=cookie.get('domain', '.linkedin.com')
                )
        except Exception as e:
            self.logger.error(f"❌ Error syncing cookies: {e}")
            
    def _is_logged_in(self):
        """Check if currently logged in to LinkedIn"""
        try:
            current_url = self.driver.current_url.lower()
            
            logged_in_patterns = [
                'linkedin.com/feed',
                'linkedin.com/in/',
                'linkedin.com/mynetwork',
                'linkedin.com/messaging',
                'linkedin.com/jobs',
                'linkedin.com/search'
            ]
            
            for pattern in logged_in_patterns:
                if pattern in current_url:
                    return True
                    
            logout_indicators = [
                "button[aria-label*='Sign out']",
                "a[href*='logout']",
                ".global-nav__me",
                "img[alt*='profile']"
            ]
            
            for selector in logout_indicators:
                if self.driver.find_elements(By.CSS_SELECTOR, selector):
                    return True
                    
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Error checking login status: {e}")
            return False
            
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
                
            print("\n" + "="*60)
            print("🔐 PLEASE LOG IN TO LINKEDIN MANUALLY")
            print("="*60)
            print("👆 Use the browser window that just opened")
            print("📧 Enter your email and password") 
            print("🔐 Complete any 2FA, captcha, etc.")
            print("⏳ Take as much time as you need!")
            print("🤖 The script will automatically detect when you're logged in")
            print("="*60)
            
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
                    print(f"⏳ Still waiting for login... {minutes_left} minutes remaining")
                    
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
            
            print("\n" + "="*80)
            print("🔍 SEARCH PAGE LOADED - PLEASE SET FILTERS MANUALLY")
            print("="*80)
            print("👆 Use the browser window to set these filters:")
            print("   1. 🔘 Click 'All filters' button")
            print("   2. 🔗 Click '2nd' connection level")
            print("   3. 🇺🇸 Click 'United States' checkbox")
            print("   4. 📊 Click 'Show results' button")
            print("")
            print("⏳ You have 15 seconds to complete this...")
            print("🤖 The script will automatically continue after 15 seconds")
            print("="*80)
            
            # Wait 15 seconds for manual filter selection
            for i in range(15, 0, -1):
                print(f"⏱️  {i} seconds remaining...")
                time.sleep(1)
            
            print("\n✅ Manual filter selection time complete!")
            self.logger.info("✅ Manual filter selection period finished - continuing with scraping")
            
            time.sleep(3)
            return True
                
        except Exception as e:
            self.logger.error(f"❌ Error in manual search setup: {e}")
            return False
            
    def scrape_profiles_with_coordinates(self, max_pages=5, max_profiles=50, delay_between_profiles=5):
        """Scrape profiles using coordinate-based clicking with comprehensive data extraction"""
        try:
            self.logger.info("🔍 Starting coordinate-based profile scraping...")
            
            # Get browser window dimensions
            window_size = self.driver.get_window_size()
            browser_width = window_size['width']
            browser_height = window_size['height']
            
            self.logger.info(f"🖥️ Browser window size: {browser_width}x{browser_height}")
            
            base_x = browser_width // 2  # Middle horizontal for all
            
            # Profile coordinates
            top_profiles = [
                (base_x, int(browser_height * 0.20), "Profile 1", "20% from top"),
                (base_x, int(browser_height * 0.33), "Profile 2", "33% from top"),
                (base_x, int(browser_height * 0.46), "Profile 3", "46% from top"),
                (base_x, int(browser_height * 0.55), "Profile 4", "55% from top"),
                (base_x, int(browser_height * 0.64), "Profile 5", "64% from top"),
                (base_x, int(browser_height * 0.73), "Profile 6", "73% from top"),
                (base_x, int(browser_height * 0.82), "Profile 7", "82% from top"),
            ]
            
            anchor_profiles = [
                (base_x, int(browser_height * 0.20), "Profile 8", "Anchor at Profile 1 position"),
                (base_x, int(browser_height * 0.33), "Profile 9", "Anchor at Profile 2 position"),
                (base_x, int(browser_height * 0.42), "Profile 10", "Anchor above Profile 3 position"),
            ]
            
            # Global tracking
            total_successful_scrapes = 0
            total_profiles_attempted = 0
            
            # Process each page
            current_page = 1
            while current_page <= max_pages and total_successful_scrapes < max_profiles:
                try:
                    print(f"\n" + "="*70)
                    print(f"📄 PAGE {current_page}/{max_pages} - PROCESSING UP TO 10 PROFILES")
                    print("="*70)
                    
                    page_successful_scrapes = 0
                    page_profiles_attempted = 0
                    
                    # Store the search page URL for this page
                    current_state = self._check_current_state()
                    if current_state != "search":
                        self.logger.warning("⚠️ Not on search page at start - attempting recovery...")
                        search_url = "https://www.linkedin.com/search/results/people/?keywords=author"
                        self.driver.get(search_url)
                        time.sleep(3)
                    
                    stored_search_url = self.driver.current_url
                    self.logger.info(f"📍 Stored search URL for page {current_page}: {stored_search_url}")
                    self.stats['search_pages'] += 1
                    
                    # Process all 10 profiles on this page
                    all_profiles = top_profiles + anchor_profiles
                    
                    for profile_num, (x, y, description, strategy) in enumerate(all_profiles, 1):
                        # Check if we've reached max profiles
                        if total_successful_scrapes >= max_profiles:
                            print(f"🎯 Reached maximum of {max_profiles} profiles - stopping")
                            break
                            
                        try:
                            page_profiles_attempted += 1
                            total_profiles_attempted += 1
                            self.stats['total_processed'] += 1
                            
                            print(f"\n🧪 PAGE {current_page} - ATTEMPT {profile_num}/10: {description.upper()}")
                            print(f"🎯 Target: {description}")
                            print(f"📐 Coordinates: ({x}, {y})")
                            print(f"📏 Strategy: {strategy}")
                            
                            # Pre-click safety check
                            current_state = self._check_current_state()
                            if current_state != "search":
                                self.logger.warning(f"⚠️ Not on search page before click - recovering...")
                                if not self._recover_to_search(stored_search_url):
                                    print(f"❌ Could not recover to search page - skipping {description}")
                                    continue
                            
                            # Perform the click based on profile type
                            click_success = False
                            
                            if profile_num <= 7:
                                # Normal profiles - scroll to top and click
                                self.logger.info("📜 Ensuring top position...")
                                self.driver.execute_script("window.scrollTo(0, 0);")
                                time.sleep(1)
                                click_success = self._coordinate_click(x, y, f"- {description}")
                                
                            else:
                                # Anchored profiles - use anchoring method
                                self.logger.info("⚓ Starting anchoring sequence...")
                                
                                # Anchor Step 1: Scroll to top
                                self.driver.execute_script("window.scrollTo(0, 0);")
                                time.sleep(2)
                                
                                # Anchor Step 2: Position mouse
                                actions = ActionChains(self.driver)
                                actions.move_by_offset(x, y)
                                actions.perform()
                                time.sleep(1)
                                
                                # Anchor Step 3: Scroll to bottom
                                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                                time.sleep(3)
                                
                                # Anchor Step 4: Click
                                actions = ActionChains(self.driver)
                                actions.click()
                                actions.perform()
                                time.sleep(1)
                                
                                # Reset mouse
                                actions = ActionChains(self.driver)
                                actions.move_by_offset(-x, -y)
                                actions.perform()
                                
                                click_success = True
                            
                            # Check result with timeout
                            if click_success:
                                self.logger.info(f"🕐 Waiting 5 seconds to check result...")
                                time.sleep(5)
                                
                                current_state = self._check_current_state()
                                current_url = self.driver.current_url
                                
                                if current_state == "profile":
                                    # SUCCESS - we're on a profile page
                                    if current_url in self.processed_urls:
                                        print(f"⚠️ {description.upper()} - DUPLICATE! Already processed: {current_url}")
                                        self.logger.warning(f"Duplicate URL: {current_url}")
                                        self.stats['duplicates_skipped'] += 1
                                    else:
                                        # NEW PROFILE - perform full scraping
                                        self.processed_urls.add(current_url)
                                        self.stats['coordinate_clicks_successful'] += 1
                                        print(f"✅ {description.upper()} SUCCESS! New profile: {current_url}")
                                        
                                        # COMPREHENSIVE DATA EXTRACTION
                                        scrape_result = self.scrape_current_profile()
                                        
                                        if scrape_result:
                                            page_successful_scrapes += 1
                                            total_successful_scrapes += 1
                                            print(f"📊 Profile fully scraped! Total: {total_successful_scrapes}/{max_profiles}")
                                        else:
                                            print(f"⚠️ Profile scraping failed for {description}")
                                    
                                    # Go back to search
                                    self.logger.info(f"⬅️ Going back from {description}...")
                                    if not self._recover_to_search(stored_search_url):
                                        self.logger.warning("⚠️ Could not return to search page")
                                        
                                elif current_state == "search":
                                    # FAILED - still on search page, click didn't work
                                    print(f"⚠️ {description.upper()} FAILED - Click didn't navigate anywhere")
                                    self.stats['coordinate_clicks_failed'] += 1
                                    
                                else:
                                    # UNKNOWN - somewhere else, recover
                                    print(f"⚠️ {description.upper()} UNKNOWN STATE - Recovering to search")
                                    self._recover_to_search(stored_search_url)
                                    self.stats['coordinate_clicks_failed'] += 1
                            else:
                                print(f"❌ {description.upper()} CLICK FAILED")
                                self.stats['coordinate_clicks_failed'] += 1
                                
                            # Delay between profiles
                            if profile_num < len(all_profiles):
                                time.sleep(delay_between_profiles)
                                
                        except KeyboardInterrupt:
                            print(f"\n⚠️ Scraping interrupted at Page {current_page}, {description}")
                            return False
                        except Exception as e:
                            self.logger.error(f"❌ Error with Page {current_page}, {description}: {e}")
                            print(f"❌ Error with {description}: {e}")
                            # Try to recover and continue
                            self._recover_to_search(stored_search_url)
                            continue
                    
                    # Page summary
                    page_success_rate = (page_successful_scrapes / 10) * 100 if page_profiles_attempted > 0 else 0
                    print(f"\n📊 PAGE {current_page} SUMMARY:")
                    print(f"🎯 Profiles Attempted: {page_profiles_attempted}")
                    print(f"✅ Successful Scrapes: {page_successful_scrapes}")
                    print(f"❌ Failed Attempts: {page_profiles_attempted - page_successful_scrapes}")
                    print(f"📈 Page Success Rate: {page_success_rate:.1f}%")
                    
                    # Move to next page (if not the last page and haven't reached max profiles)
                    if current_page < max_pages and total_successful_scrapes < max_profiles:
                        print(f"\n➡️ MOVING TO PAGE {current_page + 1}")
                        
                        # Ensure we're on search page before looking for next button
                        if self._check_current_state() != "search":
                            self._recover_to_search(stored_search_url)
                        
                        # Scroll to top to find pagination
                        self.driver.execute_script("window.scrollTo(0, 0);")
                        time.sleep(2)
                        
                        # Try to find and click next page button
                        next_clicked = False
                        next_button_selectors = [
                            "button[aria-label='Next']",
                            "button[aria-label*='Next']",
                            ".artdeco-pagination__button--next"
                        ]
                        
                        for selector in next_button_selectors:
                            try:
                                next_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                for button in next_buttons:
                                    if button.is_displayed() and button.is_enabled():
                                        self.logger.info(f"🔘 Clicking next page button...")
                                        button.click()
                                        time.sleep(5)  # Wait for page load
                                        next_clicked = True
                                        break
                                if next_clicked:
                                    break
                            except Exception as e:
                                continue
                        
                        if not next_clicked:
                            print(f"⚠️ Could not find next page button - stopping at page {current_page}")
                            break
                        else:
                            print(f"✅ Successfully moved to page {current_page + 1}")
                            current_page += 1
                    else:
                        break
                    
                except Exception as e:
                    self.logger.error(f"❌ Error processing page {current_page}: {e}")
                    current_page += 1
                    continue
            
            # Final results
            overall_success_rate = (total_successful_scrapes / total_profiles_attempted) * 100 if total_profiles_attempted > 0 else 0
            
            print(f"\n" + "="*70)
            print(f"🎉 COORDINATE-BASED SCRAPING COMPLETE!")
            print(f"📊 FINAL STATS:")
            print(f"📄 Pages Processed: {current_page}")
            print(f"🎯 Total Profiles Attempted: {total_profiles_attempted}")
            print(f"✅ Total Successful Scrapes: {total_successful_scrapes}")
            print(f"❌ Total Failed Attempts: {total_profiles_attempted - total_successful_scrapes}")
            print(f"📈 Overall Success Rate: {overall_success_rate:.1f}%")
            print(f"🌟 Unique Profiles Found: {len(self.processed_urls)}")
            print(f"📧 Emails Found: {self.stats['emails_found']}")
            print(f"📱 Phones Found: {self.stats['phones_found']}")
            print(f"🌐 Websites Found: {self.stats['websites_found']}")
            print(f"📝 Posts Found: {self.stats['posts_found']}")
            print(f"💬 Comments Found: {self.stats['comments_found']}")
            print(f"🔄 Duplicates Skipped: {self.stats['duplicates_skipped']}")
            print(f"📁 Output Directory: {self.output_dir}")
            print("="*70)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error in coordinate-based scraping: {e}")
            return False
            
    def scrape_current_profile(self):
        """Scrape the currently loaded profile page with comprehensive data extraction"""
        try:
            current_url = self.driver.current_url
            self.logger.info(f"📋 Scraping current profile: {current_url}")
            
            # Extract profile info
            profile_info = self.extract_profile_info(current_url)
            
            # Create folder with number prefix (MAINTAINED)
            clean_name = self._clean_filename(f"{self.stats['total_processed']}_{profile_info['name']}")
            person_folder = self.output_dir / clean_name
            person_folder.mkdir(exist_ok=True)
            
            # Save profile info
            info_path = person_folder / "profile_info.json"
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(profile_info, f, indent=2, ensure_ascii=False)
            
            # Download components
            pdf_success = self.download_profile_pdf(current_url, person_folder)
            time.sleep(2)
            
            picture_success = self.download_profile_picture(current_url, person_folder)
            time.sleep(2)
            
            activity_success = self.scrape_enhanced_activity(current_url, person_folder)
            time.sleep(2)
            
            results = {
                'profile_info': True,
                'pdf': pdf_success,
                'picture': picture_success,
                'activity': activity_success
            }
            
            success_count = sum(1 for v in results.values() if v == True)
            if success_count >= 3:
                self.stats['successful'] += 1
                status = "✅ SUCCESS"
            else:
                self.stats['failed'] += 1
                status = "⚠️ PARTIAL"
            
            self.logger.info(f"{status} [{self.stats['total_processed']}] {clean_name} - {success_count}/4")
            
            return results
            
        except Exception as e:
            self.stats['failed'] += 1
            self.logger.error(f"❌ Error scraping current profile: {e}")
            return False
            
    def _clean_filename(self, name):
        """Clean name for safe folder/filename"""
        clean = re.sub(r'[<>:"/\\|?*]', '_', name.strip())
        clean = re.sub(r'[^\w\s-]', '', clean)
        clean = re.sub(r'\s+', '_', clean)
        return clean[:50]
        
    def _move_downloaded_pdf(self, person_folder, expected_name="Profile.pdf"):
        """Move downloaded PDF from ~/Downloads to person folder"""
        try:
            pdf_patterns = [
                self.downloads_dir / expected_name,
                self.downloads_dir / "Profile*.pdf",
                self.downloads_dir / "*.pdf"
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
            
    def extract_contact_info(self, profile_url):
        """Extract contact information including websites by clicking Contact info"""
        try:
            self.logger.info("📞 Extracting contact information...")
            
            contact_info = {
                'email': None,
                'phone': None,
                'websites': [],
                'social_profiles': []
            }
            
            contact_selectors = [
                "a[aria-label*='Contact info']",
                "a[data-control-name*='contact_see_more']",
                "button[aria-label*='Contact info']"
            ]
            
            contact_button = None
            for selector in contact_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            contact_button = element
                            break
                    if contact_button:
                        break
                except:
                    continue
                    
            if contact_button:
                self.logger.info("🔘 Clicking Contact info...")
                contact_button.click()
                time.sleep(2)
                
                # Extract email
                email_selectors = [
                    "a[href^='mailto:']",
                    ".pv-contact-info__contact-type a"
                ]
                
                for selector in email_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            href = element.get_attribute('href')
                            text = element.text.strip()
                            
                            if href and 'mailto:' in href:
                                email = href.replace('mailto:', '').strip()
                                if self._is_valid_email(email):
                                    contact_info['email'] = email
                                    self.logger.info(f"📧 Email: {email}")
                                    self.stats['emails_found'] += 1
                                    break
                            elif text and '@' in text and self._is_valid_email(text):
                                contact_info['email'] = text
                                self.logger.info(f"📧 Email: {text}")
                                self.stats['emails_found'] += 1
                                break
                                
                        if contact_info['email']:
                            break
                    except:
                        continue
                
                # Extract phone
                phone_selectors = [
                    "a[href^='tel:']",
                    ".pv-contact-info__contact-type"
                ]
                
                for selector in phone_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            href = element.get_attribute('href')
                            text = element.text.strip()
                            
                            if href and 'tel:' in href:
                                phone = href.replace('tel:', '').strip()
                                if self._is_valid_phone(phone):
                                    contact_info['phone'] = phone
                                    self.logger.info(f"📱 Phone: {phone}")
                                    self.stats['phones_found'] += 1
                                    break
                            elif text and self._is_valid_phone(text):
                                contact_info['phone'] = text
                                self.logger.info(f"📱 Phone: {text}")
                                self.stats['phones_found'] += 1
                                break
                                
                        if contact_info['phone']:
                            break
                    except:
                        continue
                
                # Extract websites
                website_selectors = [
                    "a[href^='http']",
                    "a[href^='https']",
                    ".pv-contact-info__contact-type a",
                    ".pv-contact-info__ci-container a"
                ]
                
                for selector in website_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            href = element.get_attribute('href')
                            text = element.text.strip()
                            
                            if href and self._is_valid_website(href):
                                # Skip mailto and tel links
                                if not any(skip in href.lower() for skip in ['mailto:', 'tel:', 'linkedin.com']):
                                    website_data = {
                                        'url': href,
                                        'display_text': text if text else href,
                                        'extracted_at': datetime.now().isoformat()
                                    }
                                    
                                    # Avoid duplicates
                                    if not any(w['url'] == href for w in contact_info['websites']):
                                        contact_info['websites'].append(website_data)
                                        self.logger.info(f"🌐 Website: {href}")
                                        self.stats['websites_found'] += 1
                                        
                    except Exception as e:
                        continue
                
                # Close modal
                try:
                    close_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button[aria-label*='Dismiss']")
                    if close_buttons:
                        close_buttons[0].click()
                except:
                    pass
                    
            if contact_info['email'] or contact_info['phone'] or contact_info['websites']:
                self.stats['contact_info_found'] += 1
                
            return contact_info
            
        except Exception as e:
            self.logger.error(f"❌ Error extracting contact info: {e}")
            return {'email': None, 'phone': None, 'websites': [], 'social_profiles': []}
            
    def _is_valid_email(self, email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
        
    def _is_valid_phone(self, phone):
        """Validate phone number format"""
        clean_phone = re.sub(r'[^\d+\-\(\)\s]', '', phone)
        return len(re.findall(r'\d', clean_phone)) >= 7
        
    def _is_valid_website(self, url):
        """Validate website URL format"""
        try:
            # Basic URL validation
            if not url or len(url) < 10:
                return False
                
            # Must start with http or https
            if not url.lower().startswith(('http://', 'https://')):
                return False
                
            # Must contain a dot (domain)
            if '.' not in url:
                return False
                
            # Skip common non-website URLs
            skip_patterns = [
                'mailto:',
                'tel:',
                'linkedin.com',
                'javascript:',
                'file://',
                'ftp://'
            ]
            
            for pattern in skip_patterns:
                if pattern in url.lower():
                    return False
                    
            return True
            
        except Exception:
            return False
        
    def extract_profile_info(self, profile_url):
        """Extract comprehensive profile information"""
        try:
            name = "Unknown"
            headline = "No headline"
            location = "Unknown location"
            
            # Name
            name_selectors = [
                "h1.text-heading-xlarge",
                "h1",
                ".pv-text-details__left-panel h1"
            ]
            
            for selector in name_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    name = element.text.strip()
                    if name and len(name) > 2:
                        break
                except:
                    continue
            
            # Headline
            headline_selectors = [
                ".text-body-medium.break-words",
                ".pv-text-details__left-panel .text-body-medium"
            ]
            
            for selector in headline_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    headline = element.text.strip()
                    if headline and len(headline) > 3:
                        break
                except:
                    continue
            
            # Location
            location_selectors = [
                ".text-body-small.inline.t-black--light.break-words",
                ".pv-text-details__left-panel .text-body-small"
            ]
            
            for selector in location_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        if text and any(word in text.lower() for word in ['united states', 'usa', 'us']):
                            location = text
                            break
                    if location != "Unknown location":
                        break
                except:
                    continue
            
            # Contact info (including websites)
            contact_info = self.extract_contact_info(profile_url)
            
            profile_info = {
                'name': name,
                'headline': headline,
                'location': location,
                'url': profile_url,
                'contact_info': contact_info,
                'scraped_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"✅ Profile: {name} - {headline[:50]}")
            return profile_info
            
        except Exception as e:
            self.logger.error(f"❌ Error extracting profile: {e}")
            return {
                'name': 'Unknown', 
                'headline': 'Error', 
                'location': 'Unknown', 
                'url': profile_url,
                'contact_info': {'email': None, 'phone': None, 'websites': [], 'social_profiles': []}
            }
            
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
                "button[id*='profile-overflow-action']"
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
                    ".artdeco-dropdown__item"
                ]
                
                pdf_clicked = False
                for selector in pdf_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if element.is_displayed() and 'PDF' in element.text:
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
                "img[alt*='profile']"
            ]
            
            img_url = None
            for selector in img_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            src = element.get_attribute('src')
                            if src and 'profile' in src:
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
            
            ext = '.jpg' if 'jpg' in response.headers.get('content-type', '') else '.png'
            img_path = output_folder / f"profile_picture{ext}"
            
            with open(img_path, 'wb') as f:
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
                'profile_url': profile_url,
                'scraped_at': datetime.now().isoformat(),
                'posts': [],
                'comments': []
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
                "Comments"
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
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            # Extract posts
            post_selectors = [
                ".update-components-text.relative.update-components-update-v2__commentary span[dir='ltr']",
                ".update-components-text span[dir='ltr']",
                ".feed-shared-update-v2 .update-components-text",
                ".feed-shared-update .update-components-text"
            ]
            
            posts_found = 0
            for selector in post_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for i, element in enumerate(elements):
                        try:
                            post_text = element.get_attribute('innerHTML')
                            if not post_text:
                                post_text = element.text
                                
                            post_text = re.sub(r'<[^>]+>', '', post_text)
                            post_text = post_text.strip()
                            
                            if post_text and len(post_text) > 10:
                                post_data = {
                                    'index': posts_found + 1,
                                    'text': post_text[:2000],
                                    'extracted_at': datetime.now().isoformat()
                                }
                                
                                activity_data['posts'].append(post_data)
                                posts_found += 1
                                
                        except Exception as e:
                            continue
                    
                    if posts_found > 0:
                        break
                        
                except Exception as e:
                    continue
            
            self.logger.info(f"📝 Found {posts_found} posts")
            self.stats['posts_found'] += posts_found
            
            # Save activity data
            activity_path = output_folder / "enhanced_activity.json"
            with open(activity_path, 'w', encoding='utf-8') as f:
                json.dump(activity_data, f, indent=2, ensure_ascii=False)
                
            total_content = len(activity_data['posts']) + len(activity_data['comments'])
            self.logger.info(f"✅ Enhanced activity saved: {total_content} items total")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error in enhanced activity scraping: {e}")
            return False
            
    def close(self):
        """Close browser"""
        if hasattr(self, 'driver'):
            self.logger.info("🔒 Closing browser...")
            self.driver.quit()


def main():
    """Main function"""
    
    # Configuration - CHANGE THESE VALUES!
    MAX_PAGES = 3          # Search pages to scrape (1-10)
    MAX_PROFILES = 15      # Total profiles to process (1-100)
    DELAY_BETWEEN_PROFILES = 5  # Seconds between profiles (3-10)
    
    print("🚀 LinkedIn Integrated Safe Scraper Starting...")
    print(f"🎯 Target: {MAX_PROFILES} profiles from {MAX_PAGES} pages")
    print("✨ Features: Coordinate clicking + Manual filters + Full data extraction + Website extraction + Recovery logic")
    
    scraper = LinkedInIntegratedScraper(
        output_dir="linkedin_integrated_scrape_authors",
        headless=False
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
        
        # Scrape profiles using coordinate-based clicking with full data extraction
        success = scraper.scrape_profiles_with_coordinates(
            max_pages=MAX_PAGES,
            max_profiles=MAX_PROFILES,
            delay_between_profiles=DELAY_BETWEEN_PROFILES
        )
        
        if success:
            print("\n✅ INTEGRATED SCRAPING WITH WEBSITE EXTRACTION COMPLETED SUCCESSFULLY!")
        else:
            print("\n❌ INTEGRATED SCRAPING FAILED")
        
        input("\n⏳ Press Enter to close browser...")
        
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
    finally:
        scraper.close()


if __name__ == "__main__":
    main()