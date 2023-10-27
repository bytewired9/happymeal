from selenium import webdriver
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
    TimeoutException,
)
import traceback
from selenium.webdriver.chrome.service import Service as ChromeService
import time
import random
import os
import subprocess
import requests
import json
import hashlib
import re
from datetime import datetime
from colorama import Fore, Back, Style, init

init(autoreset=True)
cwd = os.getcwd()
version = "1.0.0"
GITHUB_URL = "https://raw.githubusercontent.com/ForgedCore8/happymeal/main/reviews.json"

global completed_surveys, surveys_target
completed_surveys = 0
surveys_target = 0


def logo():
    print(
        Fore.YELLOW
        + """              &&&&&     &&&&&           
            &&&&&&&&& &&&&&&&&&         
           &&      $&&&      &&X        
      ++++++++++++++++++++++++++++++    
     ++++++++++++++++++++++++++++++++   
     ++++++++++++++++++++++++++++++++   
    ++++++++++++++++++++++++++++++++++  
    $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$  
    &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&  
    &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&  
    &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&  
    &&&&&$ x&&&&&&&&&&&&&&&&&&x $&&&&&  
    &&&&&&x   x&&&&&&&&&&&&X   x&&&&&&  
    &&&&&&&&$                X&&&&&&&&  
    &&&&&&&&&&&&:        .$&&&&&&&&&&&  
    &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&  
    &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&  
    &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&  
    &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&  
          """
        + Style.RESET_ALL
    )
    return


def get_latest_release():
    url = "https://api.github.com/repos/ForgedCore8/happymeal/releases/latest"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get("tag_name")
    else:
        return None


def is_newer_version(current_version, latest_version):
    current = [int(x) for x in current_version.split(".")]
    latest = [int(x) for x in latest_version.split(".")]
    return latest > current


def check_and_create_config():
    """Create the config file with default values if it doesn't exist."""
    if not os.path.exists(os.path.join(cwd, "config.txt")):
        with open("config.txt", "w") as file:
            default_config = """
date=mm/dd # The date being used for the orders. e.g. 12/25 would be Christmas day.
store_number=12345 # this is the number of your mcdonalds store
ks_number=01 # This is the number of the till
auto=False # This determines if HappyMeal generates random orders or uses real orders, Overrites date field Accepts True/False (case sensitive)
"""
            file.write(default_config.strip())
            print("please edit config.txt")
            quit()


def read_config():
    config = {}
    with open("config.txt", "r") as file:
        lines = file.readlines()
        for line in lines:
            stripped_line = line.split("#")[
                0
            ].strip()  # Split by '#' and take the first part, then strip whitespace
            if not stripped_line:  # skip empty lines or full comment lines
                continue
            key, value = stripped_line.split("=")
            config[key.strip()] = value.strip()
    return config


# Initialize webdriver
def get_webdriver():
    chrome_options = webdriver.ChromeOptions()
    # chrome_options.add_argument("--headless")
    return webdriver.Chrome(options=chrome_options)


def validate_input(prompt, pattern, error_message):
    while True:
        user_input = input(prompt)
        if re.match(pattern, user_input):
            return user_input
        else:
            print(Fore.RED + error_message)


def safe_click(elem_id, retries=3, delay=2):
    for attempt in range(retries):
        try:
            # Wait until the element is present
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, elem_id)))
            element = driver.find_element(By.ID, elem_id)
            # Try clicking using JavaScript
            driver.execute_script("arguments[0].click();", element)

            return  # If clicked successfully, exit the function

        except (ElementClickInterceptedException, ElementNotInteractableException) as e:

            element.click()
            return

        except NoSuchElementException:
            if attempt < retries - 1:  # if it's not the last retry
                # time.sleep(delay)  # wait for some time before next retry
                continue
            else:
                print(f"Element with ID {elem_id} does not exist on the page.")
                return

        except Exception as e:
            print(f"Error clicking on element with ID {elem_id}: {str(e)}")
            if attempt < retries - 1:  # if it's not the last retry
                time.sleep(delay)  # wait for some time before next retry
            else:
                return


def click_elements_with_pattern():
    elements = driver.find_elements(By.CSS_SELECTOR, '[id^="R"][id$=".5"]')
    for elem in elements:
        safe_click(elem.get_attribute("id"))


def download_from_github():
    """Download the latest reviews.json from GitHub."""
    print("Getting latest review list")
    url = "https://raw.githubusercontent.com/ForgedCore8/happymeal/main/reviews.json"
    response = requests.get(url)
    with open(os.path.join(cwd, "reviews.json"), "wb") as f:
        f.write(response.content)


def is_checksum_different():
    """Check if local reviews.json checksum is different from GitHub's."""
    url = "https://raw.githubusercontent.com/ForgedCore8/happymeal/main/reviews.json"
    response = requests.get(url)

    # Generate checksum for the GitHub version
    github_checksum = hashlib.md5(response.content).hexdigest()

    # Generate checksum for the local version
    with open(os.path.join(cwd, "reviews.json"), "rb") as f:
        local_checksum = hashlib.md5(f.read()).hexdigest()

    return github_checksum != local_checksum


def load_reviews():
    """
    Load reviews from reviews.json. If it doesn't exist, or is different from the GitHub version, download it.
    """
    try:
        # Check if local file exists and if its checksum is different from the GitHub version
        if (
            not os.path.exists(os.path.join(cwd, "reviews.json"))
            or is_checksum_different()
        ):
            download_from_github()

        # Now, read the reviews from the local file
        with open(os.path.join(cwd, "reviews.json"), "r") as f:
            data = json.load(f)

        general_reviews = data["reviews"]["general"]
        breakfast_reviews = data["reviews"]["breakfast"]
        lunch_reviews = data["reviews"]["lunch"]

        return general_reviews, breakfast_reviews, lunch_reviews

    except Exception as e:
        print(f"An error occurred: {e}")
        # Return empty lists in case of an error
        return [], [], []


def select_meal_time(hour):
    if int(hour) > 11:
        safe_click("R000505")
    else:
        safe_click("R000504")
    safe_click("NextButton")


def fill_initial_data(config):

    driver.get("https://www.mcdvoice.com/Index.aspx?POSType=PieceMeal")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "InputStoreID"))
    )
    driver.find_element(By.ID, "InputStoreID").send_keys(config["store_number"])
    driver.find_element(By.ID, "InputRegisterNum").send_keys(config["ks_number"])
    global hour, transaction_number
    global completed_surveys, surveys_target
    if config["auto"] == "False":
    
        date_input = config["date"]
        month, day = date_input.split("/")
        time_input = validate_input(
            "Enter the time in HH:MM format: ",
            "^([0-9]|1[0-9]|2[0-3]):[0-5][0-9]$",
            "Incorrect time format. Please provide HH:MM.",
        )
        
        hour, minute = time_input.split(":")
        transaction_number = validate_input(
            "Enter the 4-digit transaction number: ",
            "^\d{4}$",
            "Invalid transaction number. Please provide a 4-digit number.",
        )

        amount_spent = validate_input(
            "Enter the amount spent in dollars.cents format: ",
            "^\d+\.\d{2}$",
            "Invalid amount format. Please provide dollars.cents format.",
        )
        dollars, cents = amount_spent.split(".")

        
    elif config["auto"] == "True":
        month = str(datetime.now().month)
        current_date = datetime.today()
        day_of_month = current_date.day
        selected_day = day_of_month - random.randint(0, 5)
        # If the selected_day is negative or zero (possible if today's date is in the first 5 days of the month)
        if selected_day <= 0:
            prev_month_last_date = datetime.current_date.replace(
                day=1
            ) - datetime.timedelta(days=1)
            selected_day += prev_month_last_date.day
        day = str(selected_day)
        hour = str(random.randint(5, 11))
        minute = str(random.randint(0, 59))
        ks_number = config["ks_number"]
        order_num = str(random.randint(0, 99))
        transaction_number = f"{ks_number}{order_num:02}"
        dollars = str(random.randint(1, 30))
        cents = str(random.randint(8, 99))

    Select(driver.find_element(By.ID, "InputMonth")).select_by_value(month)
    Select(driver.find_element(By.ID, "InputDay")).select_by_value(day)
    Select(driver.find_element(By.ID, "InputHour")).select_by_value(hour.zfill(2))
    Select(driver.find_element(By.ID, "InputMinute")).select_by_value(minute.zfill(2))
    driver.find_element(By.ID, "InputTransactionNum").send_keys(transaction_number)
    driver.find_element(By.ID, "AmountSpent1").send_keys(dollars)
    driver.find_element(By.ID, "AmountSpent2").send_keys(cents)
    print("Working...")
    safe_click("NextButton")


def save_to_file(order_number, validation_code):
    with open(os.path.join(cwd, "validation_codes.txt"), "a") as file:
        file.write(f"Order number {order_number} - {validation_code}\n")
    global completed_surveys
    completed_surveys += 1


def submit_review():
    if int(hour) < 11:
        selected_category = random.choice([breakfast, general])
    else:
        selected_category = random.choice([lunch, general])
    # Choose a random review from the selected category
    selected_review = random.choice(selected_category)
    safe_click("S081000")
    driver.find_element(By.ID, "S081000").send_keys(selected_review)
    print(f"review chosen: {selected_review}")
    print("Working...")
    safe_click("NextButton")


def get_validation_code():
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "ValCode"))
    )
    validation_code_element = driver.find_element(By.CLASS_NAME, "ValCode")
    validation_code = validation_code_element.text
    print(f"\r{validation_code}")
    save_to_file(transaction_number, validation_code)

def detect_opt():
    # Try to find the specific survey container segment.
    try:
        driver.find_element(By.ID, "FNSBlock9500")

        # If found, safe click the NextButton
        safe_click("NextButton")
    except NoSuchElementException:
        print("Specific survey HTML not found. Ignoring...")
        return

def survey(driver):
    global general, breakfast, lunch, completed_surveys, surveys_target

    
    try:
        general, breakfast, lunch = load_reviews()

        fill_initial_data(config)
        
        # List of IDs to safe click
        ids_to_click = [
            "R000060.1",
            "R000455.1",
            "R004000.2",
            "R001000.5",
            "R000444.1",
            "R000473.1",
            "R000474.1",
        ]
        for elem_id in ids_to_click:
            safe_click(elem_id)
            safe_click("NextButton")

        click_elements_with_pattern()
        safe_click("NextButton")

        click_elements_with_pattern()
        safe_click("NextButton")

        select_meal_time(hour)

        safe_click("NextButton")
        safe_click("R016000.2")
        safe_click("NextButton")

        click_elements_with_pattern()
        safe_click("NextButton")

        submit_review()

        ids_to_click_end = ["R000026.2", "R020000.2", "R000387.4", "R000482.5"]
        for elem_id in ids_to_click_end:
            safe_click(elem_id)
            safe_click("NextButton")
        
        detect_opt()
        get_validation_code()
    
    except Exception as e:
        # Get the current traceback information
        tb_info = traceback.extract_tb(e.__traceback__)[-1]
        file_name = tb_info.filename
        line_no = tb_info.lineno

        print(f"Unexpected error occurred in {file_name} at line {line_no}: {e}")
        driver.quit()



if __name__ == "__main__":
    os.system("cls" if os.name == "nt" else "clear")
    latest_version = get_latest_release()
    if latest_version and is_newer_version(version, latest_version):
        print("A newer version is availible!")
    logo()
    check_and_create_config()
    config = read_config()
    driver = get_webdriver()
    try:
        if config["auto"] == "False":
            while True:
                os.system("cls")
                logo()
                survey(driver)  # survey will return False if interrupted      
        elif config["auto"] == "True":
            if surveys_target is None or surveys_target == 0:
                surveys_target = int(input("How many Surveys would you like completed? : "))
            while completed_surveys < surveys_target:
                print(f"Survey Number: {completed_surveys + 1}")
                survey(driver)  # If survey returns False, we ret
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt caught. Cleaning up...")
    finally:
        driver.quit()
        # result = subprocess.run(["taskkill", "/F", "/IM", "chromedriver.exe", "/T"], capture_output=True, text=True)
        # time.sleep(1)
        # result = subprocess.run(["taskkill", "/F", "/IM", "chrome.exe", "/T"], capture_output=True, text=True) 
        # print("Finished flushing chrome processes, exiting in 5 seconds...")
        # time.sleep(5)
        quit()

