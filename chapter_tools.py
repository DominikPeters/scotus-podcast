"""The existing chapter presentation, shared by Oyez and Court alignment."""
import json,os,subprocess
from pathlib import Path

def build_chapters(sections,advocates,justices):
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

        if chapters and section_counter == len(sections) - 1 and speaker_name == chapters[0]["title"]:
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

            if sum([len(block["text"].split()) for block in text_blocks]) <= 8:
                continue

            if turn["stop"] - turn["start"] < 1.0:
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


    return chapters

def write_chapter_tags(filename,title,chapters,duration):
    tags={'title':title,'tableOfContents':{'elementID':'toc','isOrdered':True,'elements':[f'chp{i+1}' for i in range(len(chapters))]},'chapter':[]}
    for i,chapter in enumerate(chapters):
        tags['chapter'].append({'elementID':f'chp{i+1}','startTimeMs':int(chapter['start']*1000),
            'endTimeMs':int((chapters[i+1]['start'] if i+1<len(chapters) else duration)*1000),'tags':{'title':chapter['title']}})
    path=Path(filename).with_suffix('.id3.json');path.write_text(json.dumps(tags))
    try:subprocess.run(['node','add_id3v2.js',str(filename),str(path)],check=True)
    finally:path.unlink(missing_ok=True)
    return os.path.getsize(filename)
