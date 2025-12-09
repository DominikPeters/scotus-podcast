"""
Responsible for fetching oral arguments from supremecourt.gov
which have not been found on oyez yet.

Author: Dominik Peters
Date: 2023-10-22
"""

import requests
import json
import os
import sox
from bs4 import BeautifulSoup
from datetime import datetime
import time

import logging
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'}

def current_term():
    now = datetime.now()
    current_year = now.year
    # Check if September 1st of the current year has passed
    if now.month > 9 or (now.month == 9 and now.day > 1):
        return str(current_year)
    else:
        return str(current_year - 1)
    
def mp3_duration(filename):
    return sox.file_info.duration(filename)

def extract_arguments(year):
    URL = f"https://www.supremecourt.gov/oral_arguments/argument_audio/{year}"
    BASE_URL = "https://www.supremecourt.gov"

    # Send a request to the URL
    response = requests.get(URL, headers=headers)
    response.raise_for_status()  # Check that the request was successful

    # Parse the response text with BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all tables corresponding to sittings
    tables = soup.find_all("table", class_="table-bordered")

    records = []

    for table in tables:
        rows = table.find_all('tr')

        for row in rows[1:]:  # Skip the header row
            cols = row.find_all('td')
            docket_info = cols[0].find('a')
            case_name = ' '.join(cols[0].text.split()[1:])  # Remove docket number from case name

            docket_number = docket_info.text.strip()
            audio_page_url = docket_info['href'].replace('..', 'https://www.supremecourt.gov/oral_arguments')
            date_argued = int(datetime.strptime(cols[1].text.strip(), '%m/%d/%y').timestamp())

            record = {
                'docket_number': docket_number,
                'name': case_name,
                'date_argued_timestamp': date_argued,
                'audio_page_url': audio_page_url
            }
            records.append(record)

    return records

def get_from_scotus_website():
    print("Getting from SCOTUS website")

    with open("data/case_data.json", "r") as f:
        case_data = json.load(f)

    term = current_term()
    os.makedirs(f"mp3/{term}", exist_ok=True)
    if term not in case_data:
        case_data[term] = {}

    oral_arguments = extract_arguments(term)

    for oral_argument in oral_arguments:
        docket_number = oral_argument["docket_number"]
        print(f"Processing {docket_number}")

        # check if already in case_data
        if docket_number in case_data[term]:
            print(f"Already have {docket_number}, skipping")
            continue

        log.info(f"Discovered new oral argument: {docket_number}")

        mp3_url = f"https://www.supremecourt.gov/media/audio/mp3files/{docket_number}.mp3"
        oral_argument["mp3_url"] = mp3_url

        # fetch mp3
        mp3_filename = f"mp3/{term}/{docket_number}.mp3"
        mp3 = requests.get(mp3_url, headers=headers)
        if mp3.status_code == 200:
            log.info(f"Fetched mp3 for {docket_number} from {mp3_url}")
            with open(mp3_filename, "wb") as file:
                file.write(mp3.content)
            # get length of mp3 in seconds
            mp3_length = mp3_duration(mp3_filename)
            mp3_size = os.path.getsize(mp3_filename)
            oral_argument["mp3_length"] = int(mp3_length)
            oral_argument["mp3_size"] = mp3_size

            oral_argument["source"] = "scotus"
            date_argued_string = datetime.fromtimestamp(oral_argument["date_argued_timestamp"]).strftime("%B %d, %Y") # format May 17, 2021
            oral_argument["description"] = f"<p>Oral argument for {oral_argument['name']}, argued on {date_argued_string}.</p>\n<p>Once a transcript is available on oyez.org, the recording and this description will be replaced by more detailed information.</p>"

            case_data[term][docket_number] = oral_argument
            with open("data/case_data.json", "w") as f:
                json.dump(case_data, f, indent=2)
            with open("commit_message.txt", "a") as f:
                f.write(f"Add {docket_number} from supremecourt.gov")
        else:
            log.error(f"Could not fetch mp3 for {docket_number} from {mp3_url}: HTTP status code {mp3.status_code}")
        
        time.sleep(1)