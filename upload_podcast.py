"""
Responsible for:
- building rss feed
- uploading rss
- uploading mp3s

Author: Dominik Peters
Date: 2023-10-22
"""

import html 
import json
from datetime import datetime
import os

from b2sdk.v2 import *
import ftplib

import logging
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

def seconds_to_string(seconds):
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    padded_hours = str(hours).zfill(2)
    padded_minutes = str(minutes).zfill(2)
    padded_seconds = str(secs).zfill(2)

    return f"{padded_hours}:{padded_minutes}:{padded_seconds}"

def upload_to_b2(mp3_filename, b2_filename):
    log.info(f"Uploading {mp3_filename} to B2")
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    application_key = os.environ["B2_APP_KEY"]
    application_key_id = os.environ["B2_APP_KEY_ID"]
    b2_api.authorize_account("production", application_key_id, application_key)
    bucket = b2_api.get_bucket_by_name("scotus-podcast")
    bucket.upload_local_file(local_file=mp3_filename, file_name=b2_filename)
    log.info(f"B2 upload successful")

def upload_rss(rss_filename):
    # Use FTP
    server = "w008ef9a.kasserver.com"
    user = "f0161e85"
    password = os.environ["FTP_PASSWORD"]
    ftp = ftplib.FTP(server, user, password)
    ftp.cwd("podcast")
    with open("data/" + rss_filename, "rb") as file:
        ftp.storbinary(f"STOR {rss_filename}", file)
    ftp.quit()
    log.info(f"RSS upload successful: {rss_filename}")

def build_podcast(spotify=False):
    # For Spotify, we need to put chapters in the episode description
    
    with open("data/case_data.json", "r") as f:
        case_data = json.load(f)

    rss_items = []

    # latest years first
    terms = sorted(case_data.keys(), reverse=True)

    for term in terms:
        # latest arguments first
        cases = sorted(case_data[term].keys(), key=lambda x: case_data[term][x]["date_argued_timestamp"], reverse=True)

        for docket_number in cases:
            case = case_data[term][docket_number]

            # make sure case['description']} is UTF-8 encoded
            case['description'] = case['description'].encode('utf-8').decode('utf-8')

            if not "b2_url" in case:
                b2_filename = f"{term}/{docket_number}.mp3"
                mp3_filename = f"mp3/{term}/{docket_number}.mp3"
                upload_to_b2(mp3_filename, b2_filename)
                case_data[term][docket_number]["b2_url"] = f"https://f000.backblazeb2.com/file/scotus-podcast/{term}/{docket_number}.mp3"
                json.dump(case_data, open("data/case_data.json", "w"), indent=2)
                if os.path.exists(f"vtt/{term}/{docket_number}.vtt"):
                    upload_to_b2(f"vtt/{term}/{docket_number}.vtt", f"{term}/{docket_number}.vtt")
                    case_data[term][docket_number]["vtt_url"] = f"https://f000.backblazeb2.com/file/scotus-podcast/{term}/{docket_number}.vtt"
                with open("commit_message.txt", "r") as f:
                    commit_message = f.read()
                if commit_message == "":
                    with open("commit_message.txt", "w") as f:
                        f.write("Upload mp3s to B2")

            argued_date = datetime.fromtimestamp(case["date_argued_timestamp"])
            argued_date = argued_date.replace(hour=10, minute=0, second=0) # 10am ET
            argued_date_for_rss = argued_date.strftime("%a, %d %b %Y %H:%M:%S -0400")

            description = case['description']
            if spotify and 'chapters' in case:
                description += "\n\nChapters:\n"
                for chapter in case['chapters']:
                    description += f"{seconds_to_string(chapter['start'])} {chapter['title']}\n"

            # check if we have a transcript
            transcript_tag = ""
            if "vtt_url" in case:
                vtt_url = case["vtt_url"]
                transcript_tag = f'\n            <podcast:transcript url="{vtt_url}" type="text/vtt" />'

            # Build rss item
            rss_items.append(f"""    <item>
            <title>[{docket_number}] {html.escape(case['name'])}</title>
            <description><![CDATA[{description.strip()}]]></description>
            <enclosure url="{case['b2_url']}" length="{case['mp3_size']}" type="audio/mpeg"/>
            <guid>scotus_{term}_{docket_number}_v0</guid>
            <itunes:duration>{case['mp3_length']}</itunes:duration>
            <itunes:season>{term}</itunes:season>
            <pubDate>{argued_date_for_rss}</pubDate>{transcript_tag}
        </item>""")
            
    rss_items = "\n".join(rss_items)

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
    xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
    xmlns:googleplay="http://www.google.com/schemas/play-podcasts/1.0"
    xmlns:atom="http://www.w3.org/2005/Atom"
    xmlns:content="http://purl.org/rss/1.0/modules/content/"
    xmlns:podcast="https://github.com/Podcastindex-org/podcast-namespace/blob/main/docs/1.0.md">
  <channel>
    <title>Supreme Court Oral Arguments</title>
    <itunes:owner>
        <itunes:name>Dominik Peters</itunes:name>
        <itunes:email>podcast@scotusstats.com</itunes:email>
    </itunes:owner>
    <itunes:author>scotusstats.com</itunes:author>
    <itunes:explicit>false</itunes:explicit>
    <itunes:type>episodic</itunes:type>
    <itunes:category text="Government" />
    <itunes:category text="News"> 
        <itunes:category text="Politics" />
    </itunes:category>
    <description>
    <![CDATA[ A podcast feed of the audio recordings of the oral arguments at the U.S. Supreme Court. <br/>
* Podcast adds new arguments automatically and immediately after they become available on supremecourt.gov <br/>
* Detailed episode descriptions with facts about the case from oyez.org and links to docket and other information.<br/>
* Convenient chapters to skip to any exchange between a justice and an advocate (available as soon as oyez.org publishes the transcript).<br/>
Also available in video form at https://www.youtube.com/@SCOTUSOralArgument
 ]]>
    </description>
    <itunes:image href="https://scotusstats.com/podcast/podcast.jpg"/>
    <language>en-us</language>
    <link>https://scotusstats.com/podcast</link>
    <atom:link href="https://scotusstats.com/podcast/podcast.rss"
        rel="self" type="application/rss+xml" />
    {rss_items}
  </channel>
</rss>"""
    
    rss_filename = "podcast.rss" if not spotify else "podcast_spotify.rss"
    
    with open("data/" + rss_filename, "w") as file:
        file.write(rss)

    upload_rss(rss_filename)

    # # upload RSS if we changed something
    # with open("commit_message.txt", "r") as f:
    #     commit_message = f.read()
    # if commit_message != "":
    #     upload_rss("podcast.rss")
    # else:
    #     log.info("No changes made, so not uploading RSS")