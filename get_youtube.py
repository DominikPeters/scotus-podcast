"""Add confirmed public video links without changing podcast media."""
import json,logging,re
from datetime import datetime,timezone
from pathlib import Path
import requests

INDEX='https://scotusstats.com/podcast/youtube/index.json'
log=logging.getLogger(__name__)

def apply_links(data,index):
    changed=0
    for entry in index.get('recordings',{}).values():
        video=entry.get('video_id','')
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}',video):continue
        case=data.get(str(entry.get('term')),{}).get(entry.get('docket'))
        if not case:continue
        date=case.get('argument_date') or datetime.fromtimestamp(case['date_argued_timestamp'],timezone.utc).date().isoformat()
        if date!=entry.get('argument_date'):continue
        url='https://www.youtube.com/watch?v='+video
        if case.get('youtube_url')!=url:case['youtube_url']=url;changed+=1
    return changed

def get_from_youtube():
    try:
        response=requests.get(INDEX,timeout=20);response.raise_for_status();index=response.json()
        if index.get('schema_version')!=1:raise ValueError('Unsupported video index')
        path=Path('data/case_data.json');data=json.loads(path.read_text());changed=apply_links(data,index)
        if changed:
            path.write_text(json.dumps(data,indent=2))
            message=Path('commit_message.txt')
            if not message.read_text().strip():message.write_text('Add YouTube links to podcast episodes')
        log.info('Updated YouTube links for %s episodes',changed)
    except Exception:log.exception('YouTube links unavailable; retaining existing episode links')
