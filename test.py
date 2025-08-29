from selenium import webdriver
from selenium.webdriver.common.by import By

driver = webdriver.Chrome()
driver.get("http://127.0.0.1:5000/login")

# Login
driver.find_element(By.NAME, "username").send_keys("admin")
driver.find_element(By.NAME, "password").send_keys("adminpassword")
driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

# Check dashboard loaded
assert "Dashboard" in driver.page_source

driver.quit()
