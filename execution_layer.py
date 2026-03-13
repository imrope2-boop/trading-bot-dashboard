import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

WEALTHSIMPLE_URL = "https://my.wealthsimple.com/app/trade"

def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def login(driver):
    print("\nOpening Wealthsimple in Chrome...")
    driver.get(WEALTHSIMPLE_URL)
    print("\n" + "="*55)
    print("ACTION REQUIRED:")
    print("  1. Log into Wealthsimple in the Chrome window")
    print("  2. Complete your 2FA code")
    print("  3. Wait until you can see your account dashboard")
    print("  4. Come back here and press Enter to continue")
    print("="*55)
    input("\nPress Enter when you are fully logged in...")
    print("Login confirmed. Bot is now in control.")
    return True

def find_coin(driver, ticker):
    try:
        coin = ticker.replace("-USD", "").replace("-CAD", "")
        driver.get(WEALTHSIMPLE_URL)
        time.sleep(3)
        wait = WebDriverWait(driver, 15)
        search = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Search' or @type='search']")))
        search.clear()
        search.send_keys(coin)
        time.sleep(2)
        results = driver.find_elements(By.XPATH, f"//*[contains(text(),'{coin}')]")
        if results:
            results[0].click()
            time.sleep(2)
            return True
        return False
    except Exception as e:
        print(f"Error finding coin: {e}")
        return False

def execute_buy(driver, trade):
    try:
        if not find_coin(driver, trade['ticker']):
            return False
        wait = WebDriverWait(driver, 15)
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Buy')]"))).click()
        time.sleep(1)
        f = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='number' or @inputmode='decimal']")))
        f.clear()
        f.send_keys(str(trade['position_size']))
        time.sleep(1)
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Review') or contains(text(),'Continue')]"))).click()
        time.sleep(2)
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Confirm') or contains(text(),'Place')]"))).click()
        time.sleep(2)
        print(f"BUY order placed for {trade['ticker']}")
        return True
    except Exception as e:
        print(f"Buy error: {e}")
        return False

def execute_sell(driver, trade, sell_type="full"):
    try:
        if not find_coin(driver, trade['ticker']):
            return False
        wait = WebDriverWait(driver, 15)
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Sell')]"))).click()
        time.sleep(1)
        try:
            if sell_type == "half":
                btn = driver.find_element(By.XPATH, "//button[contains(text(),'50%')]")
            else:
                btn = driver.find_element(By.XPATH, "//button[contains(text(),'Max') or contains(text(),'100%')]")
            btn.click()
        except:
            f = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='number' or @inputmode='decimal']")))
            amt = round(trade['position_size'] / 2, 2) if sell_type == "half" else trade['position_size']
            f.clear()
            f.send_keys(str(sell_type))
        time.sleep(1)
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Review') or contains(text(),'Continue')]"))).click()
        time.sleep(2)
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Confirm') or contains(text(),'Place')]"))).click()
        time.sleep(2)
        print(f"SELL order placed for {trade['ticker']}")
        return True
    except Exception as e:
        print(f"Sell error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Execution Layer...")
    input("Press Enter to open Chrome...")
    driver = create_driver()
    login(driver)
    print("\nLogin test successful! Chrome will stay open.")
