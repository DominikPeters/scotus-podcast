"""
Responsible for fetching oral arguments from oyez.org
together will all necessary metadata.

Author: Dominik Peters
Date: 2023-10-22
"""

# increment this number if the description format changes
# then all descriptions will be rebuilt
CURRENT_DESCRIPTION_VERSION = "v1"

import requests
import json
import os
import sox
from datetime import datetime
import subprocess
import time
import sys
import smtplib, ssl, os

def send_email(subject, body):
    port = 465  # For SSL
    smtp_server = "w008ef9a.kasserver.com"
    user = "podcast@scotusstats.com"
    sender_email = "SCOTUS Podcast <podcast@scotusstats.com>"
    receiver_email = "Dominik Peters <mail@dominik-peters.de>"
    password = os.environ["SMTP_PASSWORD"]
    message = f"""\
From: {sender_email}
To: {receiver_email}
Subject: SCOTUS Podcast: {subject}

{body}
"""
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(user, password)
        server.sendmail(sender_email, receiver_email, message)

import logging
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

def current_term():
    now = datetime.now()
    current_year = now.year
    # Check if September 1st of the current year has passed
    if now.month > 9 or (now.month == 9 and now.day > 1):
        return str(current_year)
    else:
        return str(current_year - 1)
    
def get_argued_time(case_metadata):
    # argued date is unix timestamp
    for date in case_metadata["timeline"]:
        if date and date["event"] == "Argued":
            return date["dates"][0] 
    return None
    
def mp3_duration(filename):
    return sox.file_info.duration(filename)

def build_oyez_mp3(case_metadata, oral_argument_transcript, download_audio=True):
    # Extract advocate information
    advocates = {adv["advocate"]["name"]: f"{adv['advocate']['name']} ({adv['advocate_description'].replace('For ', 'for ').strip()})"
                for adv in case_metadata["advocates"]}

    # Extract list of presiding justices
    justices = {member["name"] : member for member in case_metadata["heard_by"][0]["members"]}

    # Extract transcript sections
    sections = oral_argument_transcript["transcript"]["sections"]

    # Get MP3
    mp3_filename = f"mp3/{case_metadata['term']}/{case_metadata['docket_number']}.mp3"
    if not os.path.exists(mp3_filename) or download_audio:
        mp3_url = oral_argument_transcript["media_file"][0]["href"]
        log.info(f"Downloading {mp3_url}")
        mp3 = requests.get(mp3_url)
        with open(mp3_filename, "wb") as file:
            file.write(mp3.content)
    # get length of mp3 in seconds
    mp3_length = mp3_duration(mp3_filename)
    mp3_size = os.path.getsize(mp3_filename)

    chapters = []

    part_number = 0
    for section_counter, section in enumerate(sections):
        part_number += 1
        part_text = f"[Section {part_number}] "
        part_text = ""
        turns = section["turns"]
        
        # Determine the headline (name of the first advocate or speaker if no advocate took a turn)
        headline = None
        for turn in turns:
            speaker_name = turn["speaker"]["name"]
            if speaker_name in advocates:
                headline = advocates[speaker_name]
                future_part_text = turn["speaker"]["last_name"] + " - "
                break
        if not headline:
            headline = turns[0]["speaker"]["name"]
            future_part_text = turns[0]["speaker"]["last_name"] + " - "

        if section_counter == len(sections) - 1 and speaker_name == chapters[0]["title"]:
            headline = headline + " (Rebuttal)"

        chapters.append({"title": part_text + headline, "start": turns[0]["start"]})
        part_text = future_part_text
        
        # List of justices who took turns
        justice_turns = []
        prev_justice = None
        for i, turn in enumerate(turns):
            current_speaker = turn["speaker"]["name"]

            if current_speaker == "John G. Roberts, Jr." and i == 0:
                continue

            text_blocks = turn["text_blocks"]
            if len(text_blocks) == 1:
                if len(text_blocks[0]["text"].split()) <= 8:
                    continue
                if current_speaker == "John G. Roberts, Jr." and len(text_blocks[0]["text"].split()) <= 15 and i == len(turns) - 1:
                    continue

            if i == len(turns) - 1:
                if current_speaker == "John G. Roberts, Jr.":
                    continue
            
            # Check if the current turn is Chief Justice and the next turn is also a justice
            is_moderation = current_speaker == "John G. Roberts, Jr."
            is_moderation = is_moderation and i < len(turns) - 1 and turns[i+1]["speaker"]["name"] in justices
            if is_moderation:
                continue

            # Avoid consecutive repetitions and consider skip_next flag
            if current_speaker in justices and current_speaker != prev_justice:
                justice_turns.append(current_speaker)
                chapters.append({"title": part_text + "Justice " + justices[current_speaker]["last_name"], "start": turn["start"]})
                prev_justice = current_speaker


    # write id3v2 info
    tags = {}
    tags["title"] = f"[{case_metadata['docket_number']}] {case_metadata['name']}"
    tags["tableOfContents"] = {
        "elementID": "toc",
        "isOrdered": True,
        "elements": [f"chp{i+1}" for i in range(len(chapters))]
    }
    tags["chapter"] = []
    for chapter_number, chapter in enumerate(chapters):
        chapter_obj = {
            "elementID": f"chp{chapter_number+1}",
            "startTimeMs": int(chapter["start"]*1000),
            "tags": {
                "title": chapter["title"],
            }
        }
        if chapter_number < len(chapters) - 1:
            chapter_obj["endTimeMs"] = int(chapters[chapter_number+1]["start"]*1000)
        else:
            chapter_obj["endTimeMs"] = int(mp3_length*1000)
        tags["chapter"].append(chapter_obj)
    json.dump(tags, open("id3.json", "w"))
    subprocess.call(["node", "add_id3v2.js", mp3_filename, "id3.json"])
    os.remove("id3.json")

    return mp3_length, mp3_size, chapters

def build_description(case_metadata):
    argued_time = get_argued_time(case_metadata)
    # Format: Jan 1, 2023
    if argued_time:
        argued_date = datetime.fromtimestamp(argued_time).strftime("%b %-d, %Y")
    else:
        argued_date = None

    is_decided = False
    for date in case_metadata["timeline"]:
        if date and date["event"] == "Decided":
            decided_time = date["dates"][0] 
            decided_time = datetime.fromtimestamp(decided_time).strftime("%b %-d, %Y")
            is_decided = True
            break
    justia_link_text = "Justia (with opinion)" if is_decided else "Justia"

    if argued_date:
        date_text = f"Argued on {argued_date}." + (f"<br>Decided on {decided_time}." if is_decided else "")
    else:
        date_text = ""
    parties_text = f"{case_metadata['first_party_label']}: {case_metadata['first_party']}"
    if not parties_text.endswith("."):
        parties_text += "."
    if case_metadata["second_party"]:
        parties_text += f"<br>{case_metadata['second_party_label']}: {case_metadata['second_party']}"
        if not parties_text.endswith("."):
            parties_text += "."

    conclusion_text = ""
    if is_decided:
        conclusion_text = f"""<p><b>Conclusion</b></p>
    {case_metadata['conclusion']}"""

    # check if there is a wikipedia article for the case (titled case_metadata['name'])
    wikipedia_url = f"https://en.wikipedia.org/wiki/{case_metadata['name'].replace(' ', '_')}"
    if requests.get(wikipedia_url).status_code == 200:
        wikipedia_text = f"""<a href="{wikipedia_url}">Wikipedia</a> &middot; """
    else:
        wikipedia_text = ""

    # Extract advocate information
    if "advocates" in case_metadata and case_metadata["advocates"]:
        advocates = {adv["advocate"]["name"]: f"{adv['advocate']['name']} ({adv['advocate_description'].replace('For ', 'for ').strip()})"
                    for adv in case_metadata["advocates"]}
        advocates_list = "<p>Advocates: <ul>" + '\n'.join(["<li>"+advocates[advocate]+"</li>" for advocate in advocates]) + "</ul></p>"
    else:
        advocates_list = ""

    description = f"""<p>{case_metadata['name']}</p>
    <p>{wikipedia_text}<a href="{case_metadata['justia_url']}">{justia_link_text}</a> &middot; <a href="https://www.supremecourt.gov/search.aspx?filename=/docket/docketfiles/html/public/{case_metadata['docket_number']}.htm">Docket</a> &middot; <a href="{case_metadata['href'].replace('api.','www.')}">oyez.org</a></p>
    <p>{date_text}</p>
    <p>{parties_text}</p>
    {advocates_list}
    <p><b>Facts of the case (from oyez.org)</b></p>
    {case_metadata['facts_of_the_case']}
    <p><b>Question</b></p>
    {case_metadata['question']}
    {conclusion_text}"""

    return description

def handle_case(case_url, scotus_record=None, download_audio=True):
    """Fetches info from oyez. If oral argument audio and transcript available,
    make a new record. Otherwise add meta data to existing scotus_record."""

    # Load the case metadata
    case_number = case_url.split("/")[-1]
    log.info(f"Handling case {case_number}")

    case_metadata = requests.get(case_url).json()

    if not "oral_argument_audio" in case_metadata or not case_metadata["oral_argument_audio"]:
        if scotus_record is None:
            log.info(f"Case {case_number} has no oral argument audio, skipping")
            return None
        else:
            log.info(f"Case {case_number} has no oral argument audio. Adding metadata to existing record.")
            try:
                description = build_description(case_metadata)
                if "description" in scotus_record and scotus_record["description"] == description:
                    log.info(f"Description of {case_number} has not changed. Skipping.")
                    return None
                scotus_record["description"] = description
                return scotus_record
            except Exception as e:
                log.exception(f"Case {case_number}: description could not be built. Skipping.")
                return None

    # Load the oral argument transcript
    log.info(f"Loading oral argument transcript for case {case_number}")
    for oral_argument_record in case_metadata["oral_argument_audio"]:
        oral_argument_url = oral_argument_record["href"]
        oral_argument_transcript = requests.get(oral_argument_url).json()
        if oral_argument_transcript["media_file"][0] and oral_argument_transcript["transcript"]:
            break
    else:
        log.error(f"Case {case_number} has no oral argument audio. Skipping.")
        return None

    mp3_length, mp3_size, chapters = build_oyez_mp3(case_metadata, oral_argument_transcript, download_audio=download_audio)
    description = build_description(case_metadata)

    argued_time = get_argued_time(case_metadata)

    record = {
        "docket_number": case_metadata["docket_number"],
        "name": case_metadata["name"],
        "date_argued_timestamp": argued_time,
        "description": description,
        "mp3_length": int(mp3_length),
        "mp3_size": mp3_size,
        "description_version": CURRENT_DESCRIPTION_VERSION,
        "chapters": chapters,
        "source": "oyez",
    }

    return record

def get_term_from_oyez(term):
    with open("data/case_data.json", "r") as f:
        case_data = json.load(f)

    os.makedirs(f"mp3/{term}", exist_ok=True)
    if term not in case_data:
        case_data[term] = {}

    oyez_case_list_url = f"https://api.oyez.org/cases?filter=term:{term}&labels=true&page=0&per_page=1000"
    oyez_case_list = requests.get(oyez_case_list_url).json()

    for case in oyez_case_list:
        case_url = case["href"]

        # check if we already have the case from oyez
        scotus_record = None
        download_audio = True
        previous_b2_url = None
        docket_number = case["docket_number"]
        if docket_number in case_data[term]:
            if case_data[term][docket_number]["source"] == "oyez":
                if case_data[term][docket_number]["description_version"] == CURRENT_DESCRIPTION_VERSION:
                    continue
                else:
                    # only description needs to be updated, so don't download audio
                    download_audio = False
                    previous_b2_url = case_data[term][docket_number]["b2_url"]
            if case_data[term][docket_number]["source"] == "scotus":
                scotus_record = case_data[term][docket_number]

        # check if argument has occurred
        argued_time = get_argued_time(case)
        if argued_time is None and scotus_record is None:
            continue

        print(f"Handling case {docket_number}: {case['name']}")
        oral_argument = handle_case(case_url, scotus_record=scotus_record, download_audio=download_audio)

        if previous_b2_url is not None:
            oral_argument["b2_url"] = previous_b2_url

        if oral_argument is not None:
            case_data[term][docket_number] = oral_argument
            with open("data/case_data.json", "w") as f:
                json.dump(case_data, f, indent=2)
            with open("commit_message.txt", "a") as f:
                if scotus_record is None:
                    f.write(f"Add case {docket_number} from oyez.org. ")
                elif oral_argument["source"] == "oyez":
                    f.write(f"Oyez transcript for {docket_number}. ")
                    send_email(f"Oyez transcript for {docket_number} available", f"""The podcast has found a new transcript for case {docket_number} on oyez.org.
The oyez link is {case_url.replace("api.", "www.")}.""")
                else:
                    f.write(f"Oyez metadata for {docket_number}. ")
                    
        
        time.sleep(1)

def get_from_oyez():
    term = current_term()
    get_term_from_oyez(term)

if __name__ == "__main__":
    # Bulk fetch all cases of a term from oyez.org
    if len(sys.argv) > 1:
        term = sys.argv[1]
        get_term_from_oyez(term)
    else:
        print("Please specify term: python3 get_oyez.py 2023")