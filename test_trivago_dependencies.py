#!/usr/bin/env python3
"""
Test script to verify all dependencies for Trivago scraper
"""

import sys
import subprocess

def test_imports():
    """Test if all required modules can be imported"""
    print("Testing imports...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.common.exceptions import (
            TimeoutException, 
            NoSuchElementException, 
            ElementClickInterceptedException,
            StaleElementReferenceException,
            WebDriverException
        )
        print("✅ Selenium imports successful")
    except ImportError as e:
        print(f"❌ Selenium import failed: {e}")
        return False
    
    try:
        import pandas as pd
        print("✅ Pandas import successful")
    except ImportError as e:
        print(f"❌ Pandas import failed: {e}")
        return False
    
    try:
        import time
        import logging
        import re
        from datetime import datetime
        print("✅ Standard library imports successful")
    except ImportError as e:
        print(f"❌ Standard library import failed: {e}")
        return False
    
    return True

def test_chrome_driver():
    """Test if Chrome driver is available"""
    print("\nTesting Chrome driver...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=options)
        driver.get("https://www.google.com")
        title = driver.title
        driver.quit()
        
        print(f"✅ Chrome driver working - loaded page with title: {title}")
        return True
    except Exception as e:
        print(f"❌ Chrome driver failed: {e}")
        print("   Please install Chrome browser and chromedriver")
        return False

def install_missing_packages():
    """Install missing packages"""
    print("\nInstalling missing packages...")
    
    packages = ['selenium', 'pandas']
    
    for package in packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ Installed {package}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {package}: {e}")

def main():
    """Main test function"""
    print("=== Trivago Scraper Dependency Test ===\n")
    
    # Test imports
    imports_ok = test_imports()
    
    if not imports_ok:
        print("\n❌ Some imports failed. Attempting to install missing packages...")
        install_missing_packages()
        print("\nRe-testing imports after installation...")
        imports_ok = test_imports()
    
    # Test Chrome driver
    if imports_ok:
        driver_ok = test_chrome_driver()
    else:
        print("\n❌ Skipping Chrome driver test due to import failures")
        driver_ok = False
    
    # Summary
    print("\n=== TEST SUMMARY ===")
    print(f"Imports: {'✅ PASS' if imports_ok else '❌ FAIL'}")
    print(f"Chrome Driver: {'✅ PASS' if driver_ok else '❌ FAIL'}")
    
    if imports_ok and driver_ok:
        print("\n🎉 All tests passed! You can run the Trivago scraper.")
        print("Run: python3 trivago_scraper_complete.py")
    else:
        print("\n❌ Some tests failed. Please fix the issues before running the scraper.")
        if not driver_ok:
            print("\nTo fix Chrome driver issues:")
            print("1. Install Google Chrome browser")
            print("2. Chrome driver should be auto-managed by Selenium 4.6+")
            print("3. If issues persist, manually install chromedriver")

if __name__ == "__main__":
    main()