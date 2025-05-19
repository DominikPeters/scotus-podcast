from get_scotus_website import get_from_scotus_website
from get_oyez import get_from_oyez
from upload_podcast import build_podcast

import sys
import logging
import re

def shorten_commit_message():
    try:
        with open("commit_message.txt", "r") as f:
            input_string = f.read()
    except FileNotFoundError:
        logger.error("Error: commit_message.txt not found.")
        return
    except Exception as e:
        logger.error(f"Error reading commit_message.txt: {e}")
        return

    logger.info(f"Original commit message: {input_string}")

    # Extract all commands using regex
    # Updated pattern to match more flexible case IDs like "24A884" or "123-456"
    case_id_pattern = r'[\w-]+'

    add_pattern = rf'Add ({case_id_pattern}) from ([\w.]+)'
    metadata_pattern = rf'Oyez metadata for ({case_id_pattern})'
    transcript_pattern = rf'Oyez transcript for ({case_id_pattern})'

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
        # metadata_matches is a list of strings (case_ids)
        if len(metadata_matches) == 1:
            output_parts.append(f"Oyez metadata for {metadata_matches[0]}")
        elif len(metadata_matches) == 2:
            output_parts.append(f"Oyez metadata for {metadata_matches[0]} and {metadata_matches[1]}")
        elif len(metadata_matches) > 2:
            joined_ids = ", ".join(metadata_matches[:-1]) + f", and {metadata_matches[-1]}"
            output_parts.append(f"Oyez metadata for {joined_ids}")

    # Process transcript commands
    if transcript_matches:
        # transcript_matches is a list of strings (case_ids)
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
    try:
        with open("commit_message.txt", "w") as f:
            f.write(output_string)
            logger.info(f"Shortened commit message: {output_string}")
    except Exception as e:
        logger.error(f"Error writing to commit_message.txt: {e}")

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