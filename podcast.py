from get_scotus_website import get_from_scotus_website
from get_oyez import get_from_oyez
from upload_podcast import build_podcast

import sys
import logging
import re

def shorten_commit_message():
    input_string = open("commit_message.txt").read()

    # Extract all commands using regex
    add_pattern = r'Add (\d+-\d+) from ([\w.]+)'
    metadata_pattern = r'Oyez metadata for (\d+-\d+)'
    transcript_pattern = r'Oyez transcript for (\d+-\d+)'
    
    # Find all matches for each pattern
    add_matches = re.findall(add_pattern, input_string)
    metadata_matches = re.findall(metadata_pattern, input_string)
    transcript_matches = re.findall(transcript_pattern, input_string)
    
    # Group add commands by source
    add_by_source = {}
    for case_id, source in add_matches:
        if source not in add_by_source:
            add_by_source[source] = []
        add_by_source[source].append(case_id)
    
    # Create shortened output
    output_parts = []
    
    # Process add commands
    for source, case_ids in add_by_source.items():
        if len(case_ids) == 1:
            output_parts.append(f"Add {case_ids[0]} from {source}")
        elif len(case_ids) == 2:
            output_parts.append(f"Add {case_ids[0]} and {case_ids[1]} from {source}")
        elif len(case_ids) > 2:
            joined_ids = ", ".join(case_ids[:-1]) + f", and {case_ids[-1]}"
            output_parts.append(f"Add {joined_ids} from {source}")
    
    # Process metadata commands
    if metadata_matches:
        if len(metadata_matches) == 1:
            output_parts.append(f"Oyez metadata for {metadata_matches[0]}")
        elif len(metadata_matches) == 2:
            output_parts.append(f"Oyez metadata for {metadata_matches[0]} and {metadata_matches[1]}")
        elif len(metadata_matches) > 2:
            joined_ids = ", ".join(metadata_matches[:-1]) + f", and {metadata_matches[-1]}"
            output_parts.append(f"Oyez metadata for {joined_ids}")
    
    # Process transcript commands
    if transcript_matches:
        if len(transcript_matches) == 1:
            output_parts.append(f"Oyez transcript for {transcript_matches[0]}")
        elif len(transcript_matches) == 2:
            output_parts.append(f"Oyez transcript for {transcript_matches[0]} and {transcript_matches[1]}")
        elif len(transcript_matches) > 2:
            joined_ids = ", ".join(transcript_matches[:-1]) + f", and {transcript_matches[-1]}"
            output_parts.append(f"Oyez transcript for {joined_ids}")
    
    # Join all parts with periods
    output_string = ". ".join(output_parts) + ("." if output_parts else "")

    # Write the shortened output
    with open("commit_message.txt", "w") as f:
        f.write(output_string)

# Create a logger object
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# log to stdout
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.INFO)
logger.addHandler(stream_handler)

try:
    get_from_scotus_website()
    get_from_oyez()
    build_podcast()
    build_podcast(spotify=True)
    shorten_commit_message()
except Exception as e:
    logging.exception(e)
    raise e