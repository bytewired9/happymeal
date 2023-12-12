"""McDonalds customer survey filler-outer-inator"""
import traceback
import time
import random
import os
import json
import hashlib
import re
import sys
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementClickInterceptedException,
    ElementNotInteractableException
)
import requests
from colorama import Fore, Style, init

init(autoreset=True)
cwd = os.getcwd()
VERSION = "1.1.0"
GITHUB_URL = "https://raw.githubusercontent.com/ForgedCore8/happymeal/main/reviews.json"

class SurveyManager:
    """
        Manages the survey numbers
    """
    def __init__(self):
        self.completed_surveys = 0
        self.surveys_target = 0

    def increment_completed_surveys(self):
        """
            Increment the survey number once completed
        """
        self.completed_surveys += 1

    def set_surveys_target(self, target):
        """
            Set the survey target
        """
        self.surveys_target = target
class DateTimeData:
    """
    Get the Date and time data based on user input or generate new data
    """
    def __init__(self, month, day, hour, minute):
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute

    @staticmethod
    def generate(auto):
        """
        Create new date time data
        """
        if auto == "True":
            current_date = datetime.today()
            selected_day = current_date.day - random.randint(0, 5)

            if selected_day <= 0:
                prev_month_last_date = current_date.replace(day=1) - timedelta(days=1)
                selected_day += prev_month_last_date.day

            month = str(current_date.month).zfill(2)
            day = str(selected_day).zfill(2)
            hour = str(random.randint(5, 11)).zfill(2)
            minute = str(random.randint(0, 59)).zfill(2)

            return DateTimeData(month, day, hour, minute)
        else:
            raise ValueError("Auto mode is not enabled.")

    @staticmethod
    def manual_input(date_input, time_input):
        """
            Parse the manual input data
        """
        month, day = date_input.split("/")
        hour, minute = time_input.split(":")
        return DateTimeData(month, day, hour, minute)
class TransactionData:
    """
        Create or parse transaction data
    """
    def __init__(self, number, dollars, cents):
        self.number = number
        self.dollars = dollars
        self.cents = cents

    @staticmethod
    def generate(ks_number):
        """
            Generate Pseudo transaction information
        """
        transaction_number = f"{ks_number}{random.randint(0, 99):02}"
        dollars = str(random.randint(1, 30))
        cents = str(random.randint(0, 99)).zfill(2)

        return TransactionData(transaction_number, dollars, cents)

    @staticmethod
    def manual_input(transaction_number, amount_spent):
        """
            Parse manual transaction information
        """
        dollars, cents = amount_spent.split(".")
        return TransactionData(transaction_number, dollars, cents)

def logo():
    """
    Prints the logo for the program at the beginning
    """
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
def get_latest_release():
    """
    yoinks the latest release version from github
    """
    url = "https://api.github.com/repos/ForgedCore8/happymeal/releases/latest"
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        return response.json().get("tag_name")
    return None
def is_newer_version(newest_version):
    """
        checks if the current version is current
    """
    current = [int(x) for x in VERSION.split(".")]
    latest = [int(x) for x in newest_version.split(".")]
    return latest > current
def check_and_create_config():
    """Create the config file with default values if it doesn't exist."""
    if not os.path.exists(os.path.join(cwd, "config.txt")):
        with open("config.txt", "w", encoding="utf-8") as file:
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
    """
        Read the current configuration file
    """
    newconfig = {}
    with open("config.txt", "r", encoding="utf-8") as file:
        lines = file.readlines()
        for line in lines:
            stripped_line = line.split("#")[
                0
            ].strip()  # Split by '#' and take the first part, then strip whitespace
            if not stripped_line:  # skip empty lines or full comment lines
                continue
            key, value = stripped_line.split("=")
            newconfig[key.strip()] = value.strip()
    return newconfig
def set_custom_headers(web_driver):
    """
        Set custom HTTP request headers for the survey
    """
    ip = f"13.{random.randint(104, 107)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
    headers = {
        "x-forwarded-for": ip
    }
    # Print the headers
    print("Setting headers for request:")
    for key, value in headers.items():
        print(f"{key}: {value}")
    # Set the headers
    web_driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {'headers': headers})
def get_webdriver():
    """
    Get the webdriver
    """
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument('--log-level=3')
    return webdriver.Chrome(options=chrome_options)
def validate_input(prompt, pattern, error_message):
    """
    Ensure user input is in the correct format
    """
    while True:
        user_input = input(prompt)
        if re.match(pattern, user_input):
            return user_input
        else:
            print(Fore.RED + error_message)
def safe_click(web_driver, elem_id, retries=3, delay=2):
    """
        safely click elements in case of failure
    """
    element = None
    for attempt in range(retries):
        try:
            # Wait until the element is present
            WebDriverWait(web_driver, 10).until(EC.presence_of_element_located((By.ID, elem_id)))
            element = web_driver.find_element(By.ID, elem_id)
            # Try clicking using JavaScript
            web_driver.execute_script("arguments[0].click();", element)

            return  # If clicked successfully, exit the function

        except (ElementClickInterceptedException, ElementNotInteractableException):

            if not element:
                return
            element.click()
            return

        except NoSuchElementException:
            if attempt < retries - 1:  # if it's not the last retry
                # time.sleep(delay)  # wait for some time before next retry
                continue

            print(f"Element with ID {elem_id} does not exist on the page.")
            return

        except Exception as e:
            print(f"Error clicking on element with ID {elem_id}: {str(e)}")
            if attempt < retries - 1:  # if it's not the last retry
                time.sleep(delay)  # wait for some time before next retry
            else:
                return
def click_elements_with_pattern(web_driver):
    """
    Click elements that will guarentee a good review
    """
    elements = web_driver.find_elements(By.CSS_SELECTOR, '[id^="R"][id$=".5"]')
    for elem in elements:
        safe_click(web_driver, elem.get_attribute("id"))
def download_reviews_from_github():
    """Download the latest reviews.json from GitHub."""
    print("Getting latest review list")
    url = "https://raw.githubusercontent.com/ForgedCore8/happymeal/main/reviews.json"
    response = requests.get(url, timeout=10)
    with open(os.path.join(cwd, "reviews.json"), "wb") as f:
        f.write(response.content)
def is_checksum_different():
    """Check if local reviews.json checksum is different from GitHub's."""
    url = "https://raw.githubusercontent.com/ForgedCore8/happymeal/main/reviews.json"
    response = requests.get(url, timeout=10)

    # Generate checksum for the GitHub version
    github_checksum = hashlib.md5(response.content).hexdigest()

    # Generate checksum for the local version
    with open(os.path.join(cwd, "reviews.json"), "rb") as f:
        local_checksum = hashlib.md5(f.read()).hexdigest()

    return github_checksum != local_checksum
def load_reviews():
    """
    Load reviews from reviews.json. If it doesn't exist, 
    or is different from the GitHub version, download it.
    """
    try:
        # Check if local file exists and if its checksum is different from the GitHub version
        if (
            not os.path.exists(os.path.join(cwd, "reviews.json"))
            or is_checksum_different()
        ):
            download_reviews_from_github()

        # Now, read the reviews from the local file
        with open(os.path.join(cwd, "reviews.json"), "r", encoding="utf-8") as f:
            data = json.load(f)

        general_reviews = data["reviews"]["general"]
        breakfast_reviews = data["reviews"]["breakfast"]
        lunch_reviews = data["reviews"]["lunch"]

        return general_reviews, breakfast_reviews, lunch_reviews

    except Exception as e:
        print(f"An error occurred: {e}")
        # Return empty lists in case of an error
        return [], [], []
def select_meal_time(web_driver, hour):
    """
        Set meal time in the mealtime section
    """
    if int(hour) > 11:
        safe_click(web_driver, "R000505")
    else:
        safe_click(web_driver, "R000504")
    safe_click(web_driver, "NextButton")
def generate_data(configuration):
    """
    Gets or generates data based on user input or config
    """
    if configuration["auto"] == "True":
        date_time_data = DateTimeData.generate(configuration["auto"])
        transaction_data = TransactionData.generate(configuration["ks_number"])
    else:
        # Assuming you have methods to validate and collect these inputs
        date_input = configuration["date"]
        time_input = validate_input(
            "Enter the time in HH:MM format: ",
            r"^([0-9]|1[0-9]|2[0-3]):[0-5][0-9]$",
            "Incorrect time format. Please provide HH:MM."
        )
        transaction_number = validate_input(
            "Enter the 4-digit transaction number: ",
            r"^\d{4}$",
            "Invalid transaction number. Please provide a 4-digit number."
        )
        amount_spent = validate_input(
            "Enter the amount spent in dollars.cents format: ",
            r"^\d+\.\d{2}$",
            "Invalid amount format. Please provide dollars.cents format."
        )


        date_time_data = DateTimeData.manual_input(date_input, time_input)
        transaction_data = TransactionData.manual_input(transaction_number, amount_spent)

    return date_time_data, transaction_data
def fill_initial_data(
        web_driver, configuration, transaction_data, date_time_data
        ):
    """
    Fill in the data required before form is started
    """
    try:
        # set_custom_headers(web_driver)
        web_driver.get("https://www.mcdvoice.com/Index.aspx?POSType=PieceMeal")
        WebDriverWait(web_driver, 10).until(
            EC.presence_of_element_located((By.ID, "InputStoreID"))
        )
        web_driver.find_element(By.ID, "InputStoreID").send_keys(configuration["store_number"])
        web_driver.find_element(By.ID, "InputRegisterNum").send_keys(configuration["ks_number"])

        Select(web_driver.find_element(By.ID, "InputMonth")).select_by_value(date_time_data.month)
        Select(web_driver.find_element(By.ID, "InputDay")).select_by_value(date_time_data.day)
        Select(web_driver.find_element(By.ID, "InputHour")).select_by_value(date_time_data.hour)
        Select(web_driver.find_element(By.ID, "InputMinute")).select_by_value(date_time_data.minute)
        web_driver.find_element(
            By.ID, "InputTransactionNum"
            ).send_keys(transaction_data.number)
        web_driver.find_element(By.ID, "AmountSpent1").send_keys(transaction_data.dollars)
        web_driver.find_element(By.ID, "AmountSpent2").send_keys(transaction_data.cents)

        print("Working...")
        safe_click(web_driver, "NextButton")
    except Exception as e:
        print(f"An error occurred: {e}")
def save_to_file(order_number, validation_code, **kwargs):
    """
    Saves code to file
    """
    manager = kwargs.get('manager', None)
    with open(os.path.join(cwd, "validation_codes.txt"), "a", encoding="utf-8") as file:
        file.write(f"Order number {order_number} - {validation_code}\n")
    if kwargs.get('manager'):
        manager.increment_completed_surveys()
def submit_review(web_driver, hour, breakfast, lunch, general):
    """
    Submits the written review to web
    """
    if int(hour) < 11:
        selected_category = random.choice([breakfast, general])
    else:
        selected_category = random.choice([lunch, general])
    # Choose a random review from the selected category
    selected_review = random.choice(selected_category)
    safe_click(web_driver, "S081000")
    web_driver.find_element(By.ID, "S081000").send_keys(selected_review)
    print(f"review chosen: {selected_review}")
    print("Working...")
    safe_click(web_driver, "NextButton")
def get_validation_code(web_driver, transaction_number, **kwargs):
    """
    Finds the validation code from the webpage
    """
    manager = kwargs.get('manager', None)
    WebDriverWait(web_driver, timeout=10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "ValCode"))
    )
    validation_code_element = web_driver.find_element(By.CLASS_NAME, "ValCode")
    validation_code = validation_code_element.text
    print(f"\r{validation_code}")
    save_to_file(transaction_number, validation_code, manager=manager)
def detect_optional_questions(web_driver):
    """
    Detect optional segment of survey
    """
    # Try to find the specific survey container segment.
    try:
        web_driver.find_element(By.ID, "FNSBlock9500")

        # If found, safe click the NextButton
        safe_click(web_driver, "NextButton")
    except NoSuchElementException:
        print("Specific survey HTML not found. Ignoring...")
        return
def survey(configuration, web_driver, **kwargs):
    """
    Main survey function
    """
    manager = kwargs.get('manager', None)
    general, breakfast, lunch = load_reviews()

    try:
        date_time_data, transaction_data = generate_data(configuration)
        fill_initial_data(
            web_driver,
            configuration,
            transaction_data, date_time_data
            )


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
            safe_click(web_driver, elem_id)
            safe_click(web_driver, "NextButton")


        click_elements_with_pattern(web_driver)

        safe_click(web_driver, "NextButton")

        click_elements_with_pattern(web_driver)
        safe_click(web_driver, "NextButton")

        select_meal_time(web_driver, date_time_data.hour)

        safe_click(web_driver, "NextButton")
        safe_click(web_driver, "R016000.2")
        safe_click(web_driver, "NextButton")

        click_elements_with_pattern(web_driver)
        safe_click(web_driver, "NextButton")

        submit_review(web_driver, date_time_data.hour, breakfast, lunch, general)

        ids_to_click_end = ["R000026.2", "R020000.2", "R000387.4", "R000482.5"]
        for elem_id in ids_to_click_end:
            safe_click(web_driver, elem_id)
            safe_click(web_driver, "NextButton")

        detect_optional_questions(web_driver)
        get_validation_code(web_driver, transaction_data.number, manager=manager)
    except Exception as e:
        # Get the current traceback information
        tb_info = traceback.extract_tb(e.__traceback__)[-1]
        print(f"Unexpected error occurred in {tb_info.filename} at line {tb_info.lineno}: {e}")
        web_driver.quit()

if __name__ == "__main__":
    os.system("cls" if os.name == "nt" else "clear")
    latest_version = get_latest_release()
    if latest_version and is_newer_version(latest_version):
        print("A newer version is availible!")
    logo()
    check_and_create_config()
    config = read_config()
    driver = get_webdriver()
    survey_manager = SurveyManager()
    try:
        if config["auto"] == "False":
            while True:
                os.system("cls")
                logo()
                survey(config, driver)  # survey will return False if interrupted
        elif config["auto"] == "True":
            if survey_manager.surveys_target is None or survey_manager.surveys_target == 0:
                survey_manager.set_surveys_target(int(
                    input("How many Surveys would you like completed? : ")))
            while survey_manager.completed_surveys < survey_manager.surveys_target:
                print(f"Survey Number: {survey_manager.completed_surveys + 1}")
                survey(config, driver, manager=survey_manager)
            print(f"Completed filling {survey_manager.surveys_target} surveys")
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt caught. Cleaning up...")
    finally:
        driver.quit()
        sys.exit()
