#!/usr/bin/env python3
"""
LinkedIn Contact Info Extraction Test Script
Tests contact button clicking + extracts email, phone, websites from modal
Uses only the most reliable CSS selectors from previous testing
"""

import time
import re
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

class ContactInfoTester:
    def __init__(self):
        self.setup_browser()
        self.test_results = {
            'profiles_tested': [],
            'extraction_methods': {},
            'success_stats': {
                'contact_buttons_found': 0,
                'modals_opened': 0,
                'emails_extracted': 0,
                'phones_extracted': 0,
                'websites_extracted': 0
            }
        }
        
    def setup_browser(self):
        """Setup Chrome browser for testing"""
        print("🌐 Setting up Chrome browser...")
        options = ChromeOptions()
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
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
            
            # Skip patterns - including ALL LinkedIn URLs
            skip_patterns = [
                'mailto:', 
                'tel:', 
                'javascript:', 
                'linkedin.com/',  # This will catch ALL LinkedIn URLs
                'www.linkedin.com/'  # Extra safety for www variant
            ]
            
            for pattern in skip_patterns:
                if pattern in url.lower():
                    return False
            return True
        except Exception:
            return False
    
    def find_contact_button(self):
        """Find contact info button using most reliable CSS selectors"""
        # Top 3 most reliable selectors from your test results
        contact_selectors = [
            {
                'name': 'CSS ID (Most Reliable)',
                'method': By.CSS_SELECTOR,
                'selector': '#top-card-text-details-contact-info'
            },
            {
                'name': 'CSS Class Backup',
                'method': By.CSS_SELECTOR,
                'selector': 'a.link-without-visited-state'
            },
            {
                'name': 'CSS Href Backup', 
                'method': By.CSS_SELECTOR,
                'selector': 'a[href*="contact-info"]'
            }
        ]
        
        for selector_info in contact_selectors:
            try:
                print(f"🔍 Testing: {selector_info['name']}")
                print(f"   Selector: {selector_info['selector']}")
                
                elements = self.driver.find_elements(selector_info['method'], selector_info['selector'])
                
                if not elements:
                    print(f"   ❌ No elements found")
                    continue
                
                # Check for clickable elements
                for element in elements:
                    try:
                        if element.is_displayed() and element.is_enabled():
                            text = element.text.strip()
                            href = element.get_attribute('href') or 'No href'
                            print(f"   ✅ Found clickable element: text='{text}', href='{href[:50]}...'")
                            print(f"   🎯 Using: {selector_info['name']}")
                            return element, selector_info['name']
                    except Exception as e:
                        continue
                
                print(f"   ⚠️ Elements found but none clickable")
                
            except Exception as e:
                print(f"   ❌ Selector failed: {e}")
                continue
        
        return None, None
    
    def extract_contact_info_from_modal(self):
        """Extract email, phone, websites from opened contact modal"""
        contact_data = {
            'email': None,
            'phone': None,
            'websites': [],
            'extraction_details': {}
        }
        
        print("📞 Extracting contact information from modal...")
        
        # Wait for modal to fully load
        time.sleep(3)
        
        # EMAIL EXTRACTION - Multiple strategies
        email_selectors = [
            # Direct email links
            "a[href*='mailto:']",
            # Common email container patterns
            "section div a[href*='mailto']", 
            # Text scanning in likely email sections
            "section:nth-child(4) div a",
            "section:last-child div a"
        ]
        
        for i, selector in enumerate(email_selectors):
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    href = element.get_attribute('href')
                    text = element.text.strip()
                    
                    print(f"🔍 Email selector {i+1}: href='{href}', text='{text}'")
                    
                    if href and 'mailto:' in href:
                        email = href.replace('mailto:', '').strip()
                        if self._is_valid_email(email):
                            contact_data['email'] = email
                            contact_data['extraction_details']['email_method'] = f"CSS selector {i+1}: {selector}"
                            print(f"📧 EMAIL FOUND: {email}")
                            break
                    elif text and '@' in text and self._is_valid_email(text):
                        contact_data['email'] = text
                        contact_data['extraction_details']['email_method'] = f"CSS text {i+1}: {selector}"
                        print(f"📧 EMAIL FOUND: {text}")
                        break
                        
                if contact_data['email']:
                    break
            except Exception as e:
                print(f"🔍 Email selector {i+1} failed: {e}")
                continue
        
        # PHONE EXTRACTION - Multiple strategies  
        phone_selectors = [
            # Direct phone links
            "a[href*='tel:']",
            # Common phone container patterns - trying various sections
            "section:nth-child(3) ul li span",
            "section:nth-child(3) ul li", 
            "section div ul li span",
            # Broader phone text search
            "*[data-test*='phone']",
            "*[aria-label*='phone']"
        ]
        
        for i, selector in enumerate(phone_selectors):
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    href = element.get_attribute('href')
                    text = element.text.strip()
                    
                    print(f"🔍 Phone selector {i+1}: href='{href}', text='{text}'")
                    
                    if href and 'tel:' in href:
                        phone = href.replace('tel:', '').strip()
                        if self._is_valid_phone(phone):
                            contact_data['phone'] = phone
                            contact_data['extraction_details']['phone_method'] = f"CSS href {i+1}: {selector}"
                            print(f"📱 PHONE FOUND: {phone}")
                            break
                    elif text and self._is_valid_phone(text):
                        contact_data['phone'] = text
                        contact_data['extraction_details']['phone_method'] = f"CSS text {i+1}: {selector}"
                        print(f"📱 PHONE FOUND: {text}")
                        break
                        
                if contact_data['phone']:
                    break
            except Exception as e:
                print(f"🔍 Phone selector {i+1} failed: {e}")
                continue
        
        # WEBSITE EXTRACTION - Multiple strategies
        website_selectors = [
            # Common website container patterns
            "section:nth-child(2) ul li a",
            "section:nth-child(2) div a",
            "section div ul li a",
            # Any external links (excluding mailto/tel/linkedin)
            "a[href^='http']"
        ]
        
        for i, selector in enumerate(website_selectors):
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    href = element.get_attribute('href')
                    text = element.text.strip()
                    
                    print(f"🔍 Website selector {i+1}: href='{href}', text='{text}'")
                    
                    if href and self._is_valid_website(href):
                        website_data = {
                            'url': href,
                            'display_text': text if text else href,
                            'extraction_method': f"CSS {i+1}: {selector}"
                        }
                        
                        # Avoid duplicates
                        if not any(w['url'] == href for w in contact_data['websites']):
                            contact_data['websites'].append(website_data)
                            print(f"🌐 WEBSITE FOUND: {href}")
                            
            except Exception as e:
                print(f"🔍 Website selector {i+1} failed: {e}")
                continue
        
        # Final summary
        print(f"\n📊 EXTRACTION SUMMARY:")
        print(f"📧 Email: {contact_data['email'] if contact_data['email'] else 'Not found'}")
        print(f"📱 Phone: {contact_data['phone'] if contact_data['phone'] else 'Not found'}")
        print(f"🌐 Websites: {len(contact_data['websites'])} found")
        
        return contact_data
    
    def close_contact_modal(self):
        """Close the contact info modal"""
        try:
            print("🔄 Closing contact modal...")
            
            # Try multiple close strategies
            close_methods = [
                # Standard close buttons
                "button[aria-label*='Dismiss']",
                "button[aria-label*='Close']", 
                ".artdeco-modal__dismiss",
                "button.artdeco-button--circle"
            ]
            
            modal_closed = False
            for selector in close_methods:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            element.click()
                            modal_closed = True
                            print(f"✅ Modal closed with: {selector}")
                            break
                    if modal_closed:
                        break
                except Exception:
                    continue
            
            if not modal_closed:
                # Try ESC key as fallback
                print("🔄 Trying ESC key...")
                actions = ActionChains(self.driver)
                actions.send_keys(Keys.ESCAPE)
                actions.perform()
            
            time.sleep(2)
            return True
            
        except Exception as e:
            print(f"❌ Error closing modal: {e}")
            return False
    
    def test_profile_contact_extraction(self, profile_index):
        """Test contact extraction for current profile"""
        print(f"\n" + "="*80)
        print(f"🧪 TESTING PROFILE {profile_index}")
        print("="*80)
        
        current_url = self.driver.current_url
        print(f"📍 Current URL: {current_url}")
        
        # Find and click contact button
        contact_button, button_method = self.find_contact_button()
        
        if not contact_button:
            print("❌ No contact button found")
            return {
                'profile_index': profile_index,
                'url': current_url,
                'contact_button_found': False,
                'error': 'No contact button found'
            }
        
        self.test_results['success_stats']['contact_buttons_found'] += 1
        
        try:
            print(f"🔘 Clicking contact button using: {button_method}")
            contact_button.click()
            time.sleep(5)  # Wait for modal
            
            # Check if modal opened (look for common modal indicators)
            modal_indicators = [
                'div[role="dialog"]',
                '.artdeco-modal',
                '.pv-contact-info'
            ]
            
            modal_found = False
            for indicator in modal_indicators:
                try:
                    modal_elements = self.driver.find_elements(By.CSS_SELECTOR, indicator)
                    if any(elem.is_displayed() for elem in modal_elements):
                        modal_found = True
                        print(f"✅ MODAL DETECTED: {indicator}")
                        break
                except:
                    continue
            
            if not modal_found:
                print("❌ Modal did not open")
                return {
                    'profile_index': profile_index,
                    'url': current_url,
                    'contact_button_found': True,
                    'button_method': button_method,
                    'modal_opened': False,
                    'error': 'Modal did not open'
                }
            
            self.test_results['success_stats']['modals_opened'] += 1
            
            # Extract contact information
            contact_data = self.extract_contact_info_from_modal()
            
            # Update success stats
            if contact_data['email']:
                self.test_results['success_stats']['emails_extracted'] += 1
            if contact_data['phone']:
                self.test_results['success_stats']['phones_extracted'] += 1
            if contact_data['websites']:
                self.test_results['success_stats']['websites_extracted'] += len(contact_data['websites'])
            
            # Close modal
            self.close_contact_modal()
            
            # Save results
            result = {
                'profile_index': profile_index,
                'url': current_url,
                'contact_button_found': True,
                'button_method': button_method,
                'modal_opened': True,
                'contact_data': contact_data,
                'success': True
            }
            
            print(f"✅ PROFILE {profile_index} TEST COMPLETE")
            return result
            
        except Exception as e:
            print(f"❌ Error during contact extraction: {e}")
            self.close_contact_modal()  # Try to close any open modal
            return {
                'profile_index': profile_index,
                'url': current_url,
                'contact_button_found': True,
                'button_method': button_method,
                'modal_opened': False,
                'error': str(e)
            }
    
    def run_test_suite(self):
        """Run the complete test suite"""
        print("🚀 LinkedIn Contact Info Extraction Test Suite")
        print("📋 Testing on 3 profiles - navigate manually between tests")
        print("="*80)
        
        for profile_num in range(1, 4):
            print(f"\n📄 Navigate to PROFILE {profile_num} and press Enter...")
            input("⏳ Press Enter when you're on the profile page...")
            
            # Test this profile
            result = self.test_profile_contact_extraction(profile_num)
            self.test_results['profiles_tested'].append(result)
            
            # Summary for this profile
            print(f"\n📊 PROFILE {profile_num} SUMMARY:")
            if result.get('success'):
                contact = result['contact_data']
                print(f"📧 Email: {contact['email'] if contact['email'] else '❌ Not found'}")
                print(f"📱 Phone: {contact['phone'] if contact['phone'] else '❌ Not found'}")
                print(f"🌐 Websites: {len(contact['websites'])} found")
                if contact['websites']:
                    for i, site in enumerate(contact['websites'], 1):
                        print(f"   {i}. {site['url']}")
            else:
                print(f"❌ Failed: {result.get('error', 'Unknown error')}")
        
        # Final comprehensive results
        self.show_final_results()
    
    def show_final_results(self):
        """Show comprehensive test results"""
        print(f"\n" + "="*80)
        print("🎉 CONTACT INFO EXTRACTION TEST RESULTS")
        print("="*80)
        
        stats = self.test_results['success_stats']
        total_profiles = len(self.test_results['profiles_tested'])
        
        print(f"\n📊 OVERALL STATISTICS:")
        print(f"👤 Profiles Tested: {total_profiles}")
        print(f"🔘 Contact Buttons Found: {stats['contact_buttons_found']}/{total_profiles}")
        print(f"📱 Modals Opened: {stats['modals_opened']}/{total_profiles}")
        print(f"📧 Emails Extracted: {stats['emails_extracted']}/{total_profiles}")
        print(f"📱 Phones Extracted: {stats['phones_extracted']}/{total_profiles}")
        print(f"🌐 Websites Extracted: {stats['websites_extracted']} total")
        
        print(f"\n📈 SUCCESS RATES:")
        button_rate = (stats['contact_buttons_found'] / total_profiles) * 100 if total_profiles > 0 else 0
        modal_rate = (stats['modals_opened'] / total_profiles) * 100 if total_profiles > 0 else 0
        email_rate = (stats['emails_extracted'] / total_profiles) * 100 if total_profiles > 0 else 0
        phone_rate = (stats['phones_extracted'] / total_profiles) * 100 if total_profiles > 0 else 0
        
        print(f"🔘 Contact Button Success: {button_rate:.1f}%")
        print(f"📱 Modal Opening Success: {modal_rate:.1f}%")
        print(f"📧 Email Extraction Success: {email_rate:.1f}%")
        print(f"📱 Phone Extraction Success: {phone_rate:.1f}%")
        
        print(f"\n📋 DETAILED RESULTS BY PROFILE:")
        for result in self.test_results['profiles_tested']:
            print(f"\n👤 Profile {result['profile_index']}:")
            print(f"   URL: {result['url']}")
            
            if result.get('success'):
                contact = result['contact_data']
                print(f"   ✅ Success - Button: {result['button_method']}")
                print(f"   📧 Email: {contact['email'] or 'None'}")
                print(f"   📱 Phone: {contact['phone'] or 'None'}")
                print(f"   🌐 Websites: {len(contact['websites'])}")
                
                # Show extraction methods that worked
                details = contact.get('extraction_details', {})
                if details.get('email_method'):
                    print(f"      📧 Email method: {details['email_method']}")
                if details.get('phone_method'):
                    print(f"      📱 Phone method: {details['phone_method']}")
                    
            else:
                print(f"   ❌ Failed: {result.get('error', 'Unknown')}")
        
        # Save results to JSON file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"contact_extraction_test_results_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {filename}")
        print("="*80)
    
    def cleanup(self):
        """Close browser"""
        print("\n⏳ Press Enter to close browser...")
        input()
        if hasattr(self, 'driver'):
            self.driver.quit()

def main():
    """Main function"""
    tester = ContactInfoTester()
    
    try:
        tester.run_test_suite()
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
    finally:
        tester.cleanup()

if __name__ == "__main__":
    main()
