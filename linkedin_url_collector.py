#!/usr/bin/env python3
"""
LinkedIn URL Collector - Smart Cookie Detection
1. Check for existing cookies - if found, ask for URL and go straight to extraction
2. If no cookies, run full manual setup then extraction
3. Output to profile_links.json as single dictionary object
"""

import requests
import time
import json
import os
import random
import re
from pathlib import Path
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.service import Service


class LinkedInURLCollector:
    def __init__(self, output_dir="linkedin_url_collector"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # File paths
        self.cookies_file = self.output_dir / "cookies.json"
        self.cache_file = self.output_dir / "search_url_cache.json"
        self.profile_links_file = self.output_dir / "profile_links.json"
        
        # Setup logging
        self._setup_logging()
        
        # Initialize profile links storage as dictionary
        self.all_profile_links = self._load_existing_profile_links()
        
        # Stats tracking
        self.stats = {
            'total_pages_processed': 0,
            'profiles_found': 0,
            'duplicates_removed': 0,
            'unique_profiles': 0,
            'pagination_successes': 0,
            'pagination_failures': 0
        }
        
    def _setup_logging(self):
        """Setup logging"""
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler = logging.FileHandler(self.output_dir / 'url_collector.log')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info("🚀 LinkedIn URL Collector initialized")
        
    def _load_existing_profile_links(self):
        """Load existing profile links from JSON file as dictionary"""
        try:
            if self.profile_links_file.exists():
                with open(self.profile_links_file, 'r') as f:
                    data = json.load(f)
                    self.logger.info(f"📂 Loaded {len(data)} existing profile links")
                    return data
        except Exception as e:
            self.logger.debug(f"No existing profile links file or error loading: {e}")
        
        return {}
        
    def _save_profile_links(self):
        """Save profile links to JSON file"""
        try:
            with open(self.profile_links_file, 'w') as f:
                json.dump(self.all_profile_links, f, indent=2)
            self.logger.info(f"💾 Saved {len(self.all_profile_links)} profile links to {self.profile_links_file}")
        except Exception as e:
            self.logger.error(f"❌ Error saving profile links: {e}")
            
    def _sanitize_name(self, raw_name):
        """Sanitize profile name using regex"""
        if not raw_name:
            return "Unknown"
            
        # Remove patterns like "View [Name]'s profile" and newlines
        # Pattern matches: \nView [anything]'s profile OR \nView [anything] profile
        cleaned = re.sub(r'\n.*View.*profile.*$', '', raw_name, flags=re.IGNORECASE)
        
        # Remove extra whitespace and newlines
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Remove unicode characters like \u2019 (smart apostrophe)
        cleaned = re.sub(r'[^\w\s\-\.\']', '', cleaned)
        
        return cleaned if cleaned else "Unknown"
        
    def _sanitize_url(self, url):
        """Sanitize LinkedIn profile URL"""
        if not url or '/in/' not in url:
            return None
            
        # Remove tracking parameters and normalize
        base_url = url.split('?')[0] if '?' in url else url
        
        # Ensure it's a valid LinkedIn profile URL
        if 'linkedin.com/in/' in base_url:
            return base_url
            
        return None
        
    def _add_new_links(self, new_links):
        """Add new links to dictionary, automatically removing duplicates"""
        duplicates_count = 0
        new_count = 0
        
        for link in new_links:
            url = link['url']
            if url not in self.all_profile_links:
                self.all_profile_links[url] = link['name']
                new_count += 1
            else:
                duplicates_count += 1
                
        self.stats['duplicates_removed'] += duplicates_count
        return new_count
        
    def check_existing_cookies(self):
        """Check if cookies file exists and is valid"""
        try:
            if not self.cookies_file.exists():
                return False
                
            with open(self.cookies_file, 'r') as f:
                cookie_data = json.load(f)
                
            # Check if cookies have required fields
            if 'cookies' in cookie_data and 'user_agent' in cookie_data:
                # Check cookie age (optional - cookies usually last weeks/months)
                timestamp = cookie_data.get('timestamp')
                if timestamp:
                    cookie_time = datetime.fromisoformat(timestamp)
                    age_days = (datetime.now() - cookie_time).days
                    self.logger.info(f"🍪 Found cookies from {age_days} days ago")
                
                return True
            else:
                self.logger.warning("⚠️ Cookies file exists but missing required fields")
                return False
                
        except Exception as e:
            self.logger.debug(f"Error checking cookies: {e}")
            return False
            
    def get_search_url_from_user(self):
        """Get search URL from user input"""
        print("\n" + "="*60)
        print("🔗 SEARCH URL INPUT")
        print("="*60)
        print("📋 Please provide your LinkedIn search URL:")
        print("💡 Example: https://www.linkedin.com/search/results/people/?keywords=author&...")
        print("")
        
        while True:
            search_url = input("🔗 Paste your search URL here: ").strip()
            
            if not search_url:
                print("❌ Please provide a URL")
                continue
                
            if 'linkedin.com/search' not in search_url:
                print("❌ Please provide a valid LinkedIn search URL")
                continue
                
            # Cache this URL for potential future use
            cache_data = {
                'url': search_url,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
            print(f"✅ Search URL accepted and cached")
            return search_url
        
    def setup_manual_phase(self):
        """Manual login and search setup"""
        print("\n" + "="*80)
        print("🔧 MANUAL SETUP: LOGIN & SEARCH")
        print("="*80)
        
        # Setup visible browser
        options = ChromeOptions()
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Anti-detection
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        service = Service("./chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        
        # Anti-detection scripts
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        try:
            # Navigate to LinkedIn
            print("🌐 Opening LinkedIn...")
            driver.get("https://www.linkedin.com")
            time.sleep(2)
            
            # Wait for user to complete everything
            print("\n" + "="*60)
            print("⏳ PLEASE COMPLETE ALL STEPS:")
            print("="*60)
            print("🔐 1. Log in to LinkedIn")
            print("🔍 2. Go to search page")
            print("🔤 3. Search for your keyword (e.g., 'author')")
            print("🔘 4. Set filters (All filters → 2nd connections → United States)")
            print("📊 5. Click 'Show results'")
            print("✅ 6. Press ENTER when you're on the final search results page...")
            input()
            
            # Extract cookies
            print("🍪 Extracting cookies...")
            cookies = driver.get_cookies()
            
            cookie_data = {
                'cookies': cookies,
                'timestamp': datetime.now().isoformat(),
                'user_agent': driver.execute_script("return navigator.userAgent;")
            }
            
            # Always overwrite cookies file
            with open(self.cookies_file, 'w') as f:
                json.dump(cookie_data, f, indent=2)
                
            print(f"✅ Cookies saved to {self.cookies_file}")
            
            # Cache the search URL
            current_url = driver.current_url
            cache_data = {
                'url': current_url,
                'timestamp': datetime.now().isoformat()
            }
            
            # Always overwrite cache file
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
            print(f"✅ Search URL cached: {current_url}")
            print("✅ Setup complete!")
            
            return current_url
            
        except Exception as e:
            self.logger.error(f"❌ Error in manual setup: {e}")
            return None
        finally:
            driver.quit()
            print("🔒 Browser closed")
            
    def setup_headless_browser(self, search_url):
        """Setup headless browser with cookies"""
        try:
            # Load cookies
            if not self.cookies_file.exists():
                raise Exception("Cookies file not found. Run setup first.")
                
            with open(self.cookies_file, 'r') as f:
                cookie_data = json.load(f)
                
            # Setup headless browser
            options = ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            options.add_argument(f'--user-agent={cookie_data.get("user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")}')
            
            # Anti-detection
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            service = Service("./chromedriver")
            driver = webdriver.Chrome(service=service, options=options)
            
            # Anti-detection scripts
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Navigate to LinkedIn first
            driver.get("https://www.linkedin.com")
            time.sleep(1)
            
            # Add cookies
            for cookie in cookie_data['cookies']:
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    self.logger.debug(f"Could not add cookie: {e}")
                    
            # Navigate to search URL
            self.logger.info(f"🌐 Navigating to search URL: {search_url}")
            driver.get(search_url)
            time.sleep(3)
            
            return driver
            
        except Exception as e:
            self.logger.error(f"❌ Error setting up headless browser: {e}")
            return None
            
    def extract_profile_links_from_page(self, driver, page_number):
        """Extract profile links from current page"""
        try:
            self.logger.info(f"🔍 Extracting profile links from page {page_number}")
            
            page_links = []
            
            # CSS selector for profile links
            for i in range(1, 11):  # LinkedIn shows 10 profiles per page
                try:
                    selector = f"ul.ycqHEtWUzSkZHnfXvWPTWXzsHyguohSKGiJViRM li:nth-child({i}) .t-16 a"
                    
                    profile_links = driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for link in profile_links:
                        href = link.get_attribute("href")
                        if href and '/in/' in href:
                            raw_name = link.text.strip()
                            clean_name = self._sanitize_name(raw_name)
                            sanitized_url = self._sanitize_url(href)
                            
                            if sanitized_url and clean_name:
                                page_links.append({
                                    'name': clean_name,
                                    'url': sanitized_url
                                })
                                self.logger.debug(f"📋 Profile {i}: {clean_name} - {sanitized_url}")
                                break
                                
                except Exception as e:
                    self.logger.debug(f"❌ Error extracting profile {i}: {e}")
                    continue
            
            profiles_found = len(page_links)
            self.stats['profiles_found'] += profiles_found
            
            print(f"✅ Found {profiles_found} profiles on page {page_number}")
            
            return page_links
            
        except Exception as e:
            self.logger.error(f"❌ Error extracting profile links from page {page_number}: {e}")
            return []
            
    def click_next_page(self, driver):
        """Click next page button"""
        try:
            self.logger.info("📄 Looking for Next page button...")
            
            # Scroll to bottom to find pagination
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(1, 2))
            
            # Try to find and click next page button
            next_button_selectors = [
                "button[aria-label='Next']",
                "button[aria-label*='Next']",
                ".artdeco-pagination__button--next"
            ]
            
            for selector in next_button_selectors:
                try:
                    next_buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                    for button in next_buttons:
                        if button.is_displayed() and button.is_enabled():
                            self.logger.info(f"🔘 Clicking next page button...")
                            
                            # Scroll button into view and click
                            driver.execute_script("arguments[0].scrollIntoView(true);", button)
                            time.sleep(random.uniform(0.5, 1))
                            button.click()
                            
                            # Wait for page load (shorter wait time)
                            page_load_wait = random.uniform(2, 4)
                            self.logger.info(f"⏳ Waiting {page_load_wait:.1f}s for next page to load...")
                            time.sleep(page_load_wait)
                            
                            self.stats['pagination_successes'] += 1
                            return True
                            
                except Exception as e:
                    self.logger.debug(f"Next button selector failed: {e}")
                    continue
            
            self.logger.warning("⚠️ Could not find next page button")
            self.stats['pagination_failures'] += 1
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Error clicking next page button: {e}")
            self.stats['pagination_failures'] += 1
            return False
            
    def collect_urls_automated(self, search_url, max_pages=5):
        """Automated headless URL collection"""
        print(f"\n" + "="*80)
        print(f"🤖 AUTOMATED URL COLLECTION ({max_pages} PAGES)")
        print("="*80)
        
        driver = self.setup_headless_browser(search_url)
        if not driver:
            return False
            
        try:
            current_page = 1
            
            while current_page <= max_pages:
                try:
                    print(f"\n📄 PROCESSING PAGE {current_page}/{max_pages}")
                    
                    # Extract profile links from current page
                    page_links = self.extract_profile_links_from_page(driver, current_page)
                    
                    if not page_links:
                        print(f"⚠️ No profiles found on page {current_page} - stopping")
                        break
                    
                    # Add new links to dictionary (automatically removes duplicates)
                    new_count = self._add_new_links(page_links)
                    duplicates_count = len(page_links) - new_count
                    
                    print(f"📊 Page {current_page}: {len(page_links)} found, {new_count} new, {duplicates_count} duplicates")
                    
                    # Save progress after each page
                    self._save_profile_links()
                    
                    self.stats['total_pages_processed'] += 1
                    
                    # Move to next page (if not the last page)
                    if current_page < max_pages:
                        print(f"➡️ Moving to page {current_page + 1}")
                        
                        if self.click_next_page(driver):
                            print(f"✅ Successfully moved to page {current_page + 1}")
                            current_page += 1
                        else:
                            print(f"⚠️ Could not find next page button - stopping at page {current_page}")
                            break
                    else:
                        current_page += 1  # Exit loop
                        
                except Exception as e:
                    self.logger.error(f"❌ Error processing page {current_page}: {e}")
                    current_page += 1
                    continue
            
            # Final save
            self._save_profile_links()
            self.stats['unique_profiles'] = len(self.all_profile_links)
            
            # Print final results
            print(f"\n" + "="*70)
            print(f"🎉 URL COLLECTION COMPLETE!")
            print(f"📊 FINAL STATS:")
            print(f"📄 Pages Processed: {self.stats['total_pages_processed']}")
            print(f"🔍 Total Profiles Found: {self.stats['profiles_found']}")
            print(f"🔄 Duplicates Removed: {self.stats['duplicates_removed']}")
            print(f"🌟 Unique Profiles in Dictionary: {self.stats['unique_profiles']}")
            print(f"📄 Pagination Successes: {self.stats['pagination_successes']}")
            print(f"📄 Pagination Failures: {self.stats['pagination_failures']}")
            print(f"📁 Output File: {self.profile_links_file}")
            print("="*70)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error in automated collection: {e}")
            return False
        finally:
            driver.quit()
            print("🔒 Headless browser closed")


def main():
    """Main function"""
    
    # CONFIGURABLE PARAMETERS - EASY TO MODIFY
    MAX_PAGES = 100  # Number of search pages to process (1-20)
    
    print("🚀 LinkedIn URL Collector - Smart Cookie Detection")
    print(f"🎯 Target: Collect profile URLs from {MAX_PAGES} pages")
    print("✨ Features: Smart cookie detection + Fast headless mode + Dictionary format")
    print("🔄 Flow: Check cookies → Use cached OR manual setup → Automated collection")
    print("📊 Output: Single JSON object {url: name, url: name, ...}")
    
    collector = LinkedInURLCollector()
    
    try:
        # Check if cookies exist
        has_cookies = collector.check_existing_cookies()
        search_url = None
        
        if has_cookies:
            print("\n✅ COOKIES FOUND - FAST MODE")
            print("🚀 Skipping manual login - using existing authentication")
            
            # Get search URL from user
            search_url = collector.get_search_url_from_user()
            
        else:
            print("\n❌ NO COOKIES FOUND - FULL SETUP MODE")
            print("🔧 Running complete manual setup...")
            
            # Run full manual setup
            search_url = collector.setup_manual_phase()
            
            if not search_url:
                print("❌ Manual setup failed")
                return
        
        print(f"\n⏳ Starting automated collection in 3 seconds...")
        time.sleep(3)
        
        # Run automated collection
        success = collector.collect_urls_automated(search_url=search_url, max_pages=MAX_PAGES)
        
        if success:
            print("\n✅ LINKEDIN URL COLLECTION COMPLETED SUCCESSFULLY!")
            print("\n📋 JSON Structure:")
            print('   "linkedin.com/in/profile1": "John Smith",')
            print('   "linkedin.com/in/profile2": "Jane Doe",')
            print('   ...')
        else:
            print("\n❌ URL COLLECTION FAILED")
                
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")


if __name__ == "__main__":
    main()