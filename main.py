from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
from joblib import Parallel, delayed
import os
from datetime import datetime, timedelta
import pytz
import re
from selenium.webdriver.common.alert import Alert
import time


def init_driver():
    options = webdriver.ChromeOptions()
    #options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-dev-shm-usage')
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=options)
    time.sleep(2)
    return driver

def convert_date(game, date, event_url):

    # Map weekday names to Python weekday numbers
    WEEKDAY_MAP = {
        "Monday":    0,
        "Tuesday":   1,
        "Wednesday": 2,
        "Thursday":  3,
        "Friday":    4,
        "Saturday":  5,
        "Sunday":    6,
    }

    PACIFIC = pytz.timezone("US/Pacific")

    """
    Parse dt_str in one of:
      - "MM/DD/YYYY h:mm AM/PM PDT"
      - "Last <Weekday> at h:mm AM/PM PDT"
      - "Today at h:mm AM/PM PDT"
      - "Yesterday at h:mm AM/PM PDT"
    and return "YYYY/MM/DD".
    """
    # 1) Try absolute date first
    try:
        return datetime.strptime(date, "%m/%d/%Y %I:%M %p PST") \
                       .strftime("%Y/%m/%d")
    except ValueError:
        pass

    # Get now in PDT (with date)
    now = datetime.now(PACIFIC)

    # 2) "Last <Weekday> at … PDT"
    m = re.match(r"Last (\w+) at \d{1,2}:\d{2} [AP]M PST", date)
    if m:
        target_wd = WEEKDAY_MAP[m.group(1)]
        # how many days back to get *last* target weekday?
        days_back = (now.weekday() - target_wd + 7) % 7 or 7
        last_date = now - timedelta(days=days_back)
        return last_date.strftime("%Y/%m/%d")

    # 3) "Today at … PDT"
    if date.startswith("Today at"):
        return now.strftime("%Y/%m/%d")
    
    # 4) Yesterday at …
    if date.startswith("Yesterday at"):
        yesterday = now - timedelta(days=1)
        return yesterday.strftime("%Y/%m/%d")
    
    # 4) Tomorrow at …
    if date.startswith("Tomorrow at"):
        tomorrow = now + timedelta(days=1)
        return tomorrow.strftime("%Y/%m/%d")

    print("== ERROR == Invalid date format", date, event_url)
    log_file = open(f"{game}/log.txt", "a")
    log_file.write(f"{event_url}, {date}\n")
    log_file.close()


def get_df_from_csv(filename):
    try:
        df = pd.read_csv(f"{filename}")
        return df
    except:
        return {}
    
def remove_duplicates_from_csv(filename):
    df = pd.read_csv(f"{filename}")
    print(f"===== {filename} df len before drop_duplicates", len(df))
    df.drop_duplicates(inplace=True)
    print(f"===== {filename} df len after drop_duplicates", len(df))

    df.sort_values(by=["DATE"], ascending=False, inplace=True)
    df.to_csv(f"{filename}", index=False, encoding='utf-8')
    
def save_to_csv(data, filename):
    if not os.path.exists(f"{filename}"):
        if "events" in filename:
            df = pd.DataFrame(columns=["DATE", "EVENT_URL", "ORGANIZER", "PLAYER_COUNT"])
        elif "players" in filename:
            df = pd.DataFrame(columns=["PLAYER_NAME", "DATE", "EVENT_URLS"])
        df.to_csv(f"{filename}", index=False)
    
    if "events" in filename:
        df = pd.DataFrame(data) #need to convert dict->dataframe
        df.sort_values(by=["DATE"], inplace=True)
    elif "players" in filename:
        df = data #already a dataframe
        df.sort_values(by=["DATE"], ascending=False, inplace=True)

    df.to_csv(f"{filename}", index=False, header=False, mode='a', encoding='utf-8')

def scrape_players(game, events_filename, n_jobs):
    players_df = get_df_from_csv(f"{game}/players.csv")
    events_df = get_df_from_csv(events_filename)
    events_diff_df = events_df
    events_df.sort_values(by=["DATE"], ascending=False, inplace=True)
    if type(players_df) == pd.DataFrame:
        events_diff_df = events_df[~events_df["EVENT_URL"].isin(players_df["EVENT_URLS"])]
        
    checked_urls_file = open(f"{game}/checked_urls.txt", "a+")
    checked_event_urls = set(checked_urls_file.readlines())
    checked_urls_file.close()

    current_time = time.time()
    Parallel(n_jobs=n_jobs)(delayed(scrape_players_helper)(game, n_jobs, current_time, index, events_diff_df, checked_event_urls) for index in range(n_jobs))


def scrape_players_helper(game, n_jobs, current_time, index, events_diff_df, checked_event_urls):
    driver = init_driver()
    players_dict = {} 
    checked_urls_file = open(f"{game}/checked_urls_{index}.txt", "a+")
    
    while index < len(events_diff_df):
        event_row = events_diff_df.iloc[index]
        row_dict = event_row.to_dict()
        event_url = row_dict["EVENT_URL"]
        if event_url in checked_event_urls:
            index += n_jobs
            continue

        date = row_dict["DATE"]

        driver.get(event_url)
        time.sleep(5)
        if index < n_jobs:
            time.sleep(5)
        
        try:
            player_column_elements = driver.find_elements(By.XPATH, '//*[@class=" Player-column"]')
        except:
            # Cookies prompt
            try:
                result_element = driver.find_element(By.XPATH, '//*[@id="necessaryOnlyButton"]')
                result_element.click()
                time.sleep(1)
                player_column_elements = driver.find_elements(By.XPATH, '//*[@class=" Player-column"]')
            except Exception:
                print("Cookies button error")
                pass

        for player_column_element in player_column_elements:
            player_url_element = player_column_element.find_element(By.XPATH, "./div/div/a")
            player_url = player_url_element.get_attribute("href")

            if player_url not in players_dict:
                players_dict[player_url] = [[date], [event_url]]
                next

            # if player already exists in dict, append to both date and event_url lists
            players_dict[player_url][0].append(date)
            players_dict[player_url][1].append(event_url)


        if index % (n_jobs*10) == 0 or index == 0:
            print("--- Elapsed time", time.time() - current_time, "Index", index, "date", date, "event_url", event_url, "len of players_dict", len(players_dict.keys()))
        
        index += n_jobs
        checked_urls_file.write(event_url + "\n")
        checked_urls_file.flush()

    checked_urls_file.close()
    
    player_data_list = []
    for player_url, values in players_dict.items():
        for date, event_url in zip(values[0], values[1]):
            player_data_list.append([player_url, date, event_url])
    df = pd.DataFrame(player_data_list, columns=["PLAYER_URL", "DATE", "EVENT_URLS"])
    save_to_csv(df, f"{game}/players.csv")

    driver.quit()


def scrape_events(game, driver, url, current_events, date_cutoff, filename="events"):
    
    driver.get(url)
    time.sleep(5)
    
    # technically can ignore the cookies prompt
    try:
        result_element = driver.find_element(By.XPATH, '//*[@id="necessaryOnlyButton"]')
        result_element.click()
        time.sleep(2)
    except Exception as e:
        print("Cookies button error", e)
        pass

    result_element = driver.find_element(By.XPATH, '//*[@id="tournament-filter-results"]')
    result_element.click()
    time.sleep(2)
    page_num = 1
    bool_flag = True

    while bool_flag:
        tbody_element = driver.find_element(By.TAG_NAME, "tbody")
        row_elements = tbody_element.find_elements(By.TAG_NAME, "tr")

        for row_element in row_elements:
            event_data_dict = {
                "DATE": "",
                "EVENT_URL": "",
                "ORGANIZER": "",
                "PLAYER_COUNT": ""
            }
            date_element = row_element.find_element(By.XPATH, './td[1]')
            date = date_element.text
            event_url_element = row_element.find_element(By.XPATH, './td[2]/a')  # Find all cells
            event_url = event_url_element.get_attribute("href")
            organizer_element = row_element.find_element(By.XPATH, './td[4]')
            organizer = organizer_element.text
            player_count_element = row_element.find_element(By.XPATH, './td[8]')
            player_count = player_count_element.text

            date_parsed = convert_date(game, date, event_url)
            event_data_dict["DATE"] = date_parsed
            event_data_dict["EVENT_URL"] = event_url
            event_data_dict["ORGANIZER"] = organizer
            event_data_dict["PLAYER_COUNT"] = player_count

            try:
                if date_parsed <= date_cutoff:
                    bool_flag = False
                    print("----- date limit reached", date_parsed)
                    break
            except:
                pass

            if event_url in current_events:
                continue

            save_to_csv([event_data_dict], filename)
    
        try:
            next_element = driver.find_element(By.XPATH, '//*[@id="tournament-table_next"]')
            try:
                # Wait until the element is clickable
                time.sleep(1)
                element = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="tournament-table_next"]'))
                )
                next_element = driver.find_element(By.XPATH, '//*[@id="tournament-table_next"]')
                next_element.click()
                page_num += 1
                print("--- Element is clickable, Next Page", page_num)
                time.sleep(6)

            except:
                print("Element is NOT clickable!")
                break
            
        except Exception as e:
            print("Next button error", e)
            break

    driver.quit()

def start_scrape_events(game="StarWarsUnlimited", date_cutoff="2024/08/01"):
    events_filename = f"{game}/events.csv"
    current_events_df = get_df_from_csv(events_filename)
    try:
        current_events = current_events_df["EVENT_URL"].tolist()
    except:
        current_events = []

    driver = init_driver()
    url = f"https://melee.gg/Tournament/Index?ordering=StartDate&filters={game}%2CEnded&mode=Table"
    scrape_events(game, driver, url, current_events, date_cutoff, filename=events_filename)

    remove_duplicates_from_csv(events_filename)

def start_scrape_players(game, events_filename = "combined_events_20250701"):
    n_jobs = 4 # adjust based on your machine
    scrape_players(game, events_filename, n_jobs)

    players_filename = f"{game}/players.csv"
    remove_duplicates_from_csv(players_filename)

    # combine the checked_urls_{index}.txt into checked_urls.txt file
    checked_urls_file = open(f"{game}/checked_urls.txt", "a+")
    for i in range(n_jobs):
        file = open(f"{game}/checked_urls_{i}.txt", "r")
        lines = file.readlines()
        for line in lines:
            checked_urls_file.write(line)
        file.close()
        os.remove(f"{game}/checked_urls_{i}.txt")

    checked_urls_file.close()


def main():
    game = "StarWarsUnlimited" # Melee partnership started in 2024/09
    #game = "Lorcana" # Melee partnership started in 2024/08? and ended in 2025/07?
    date_cutoff = "2026/01/01"

    start_scrape_events(game, date_cutoff)
    events_filename = f"{game}/events.csv"
    remove_duplicates_from_csv(events_filename)
    start_scrape_players(game, events_filename)   


# Example usage
if __name__ == "__main__":
    main()
