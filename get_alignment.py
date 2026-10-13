"""Prefer validated Court alignment while retaining independent Oyez descriptions."""
from datetime import datetime,timezone
import argparse,hashlib,json,logging,os,shutil,re,html
from pathlib import Path
from urllib.parse import urlsplit
import requests
from chapter_tools import build_chapters,write_chapter_tags
from get_oyez import build_vtt_transcript

INDEX='https://scotusstats.com/podcast/alignment/index.json'
log=logging.getLogger(__name__)

def fetch_json(url,limit=2097152):
    p=urlsplit(url)
    if p.scheme!='https' or p.hostname!='scotusstats.com' or not p.path.startswith('/podcast/alignment/'):raise ValueError('Unexpected alignment endpoint')
    r=requests.get(url,timeout=30);r.raise_for_status()
    if len(r.content)>limit:raise ValueError('Alignment export too large')
    return r.json(),r.content

def chapter_inputs(recording):
    advocates={};justices={}
    for section in recording['sections']:
        for turn in section['turns']:
            person=turn['speaker'];name=person['name']
            if person['kind']=='justice':justices[name]=person
            else:advocates[name]=name+(' ('+person['role']+')' if person.get('role') else '')
    return recording['sections'],advocates,justices

def file_hash(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()

def obtain_audio(recording,path):
    expected=recording['audio']['sha256']
    if path.exists() and file_hash(path)==expected:return
    url=recording['audio']['url'];p=urlsplit(url)
    if p.scheme!='https' or p.hostname not in ('supremecourt.gov','www.supremecourt.gov'):raise ValueError('Official audio required')
    temporary=path.with_suffix('.download');h=hashlib.sha256()
    try:
        with requests.get(url,stream=True,timeout=30) as response:
            response.raise_for_status()
            with open(temporary,'wb') as out:
                for block in response.iter_content(65536):out.write(block);h.update(block)
        if h.hexdigest()!=expected:raise ValueError('Official audio differs from the aligned source; retaining the published episode')
        temporary.replace(path)
    finally:temporary.unlink(missing_ok=True)

def apply_recording(data,entry,recording,dry_run=False):
    term,docket=recording['term'],recording['docket']
    if recording.get('schema_version')!=1 or not re.fullmatch(r'\d{4}',term) or not re.fullmatch(r'\d{2}(?:-\d+|[A-Z]\d+)',docket):raise ValueError('Invalid recording schema or identity')
    existing=data.get(term,{}).get(docket,{})
    if recording['recording_id']!=entry['recording_id'] or term!=entry['term'] or docket!=entry['docket']:raise ValueError('Export identity differs')
    date=recording['argument_date']
    previous=existing.get('argument_date') or (datetime.fromtimestamp(existing['date_argued_timestamp'],timezone.utc).date().isoformat() if existing.get('date_argued_timestamp') else None)
    if previous and previous!=date:
        log.warning('Multiple hearings for %s: retaining existing episode; owner decision needed',docket);return None
    if existing.get('alignment_revision')==entry['revision']:return None
    chapters=build_chapters(*chapter_inputs(recording))
    result={'recording':recording['recording_id'],'revision':entry['revision'],'chapters':chapters}
    if dry_run:return result
    path=Path('mp3')/term/(docket+'.mp3');path.parent.mkdir(parents=True,exist_ok=True)
    obtain_audio(recording,path);tagged=path.with_suffix('.aligned.mp3');shutil.copyfile(path,tagged)
    try:size=write_chapter_tags(tagged,f"[{docket}] {recording['case_name']}",chapters,recording['audio']['duration_seconds']);tagged.replace(path)
    finally:tagged.unlink(missing_ok=True)
    (Path('vtt')/term).mkdir(parents=True,exist_ok=True)
    build_vtt_transcript({'term':term,'docket_number':docket},{'transcript':{'sections':recording['sections']}})
    record=dict(existing)
    record.update(docket_number=docket,name=recording['case_name'],argument_date=date,
        date_argued_timestamp=existing.get('date_argued_timestamp') or int(datetime.fromisoformat(date).replace(tzinfo=timezone.utc).timestamp()),
        chapters=chapters,mp3_length=int(recording['audio']['duration_seconds']),mp3_size=size,source='scotus',
        audio_source='scotus',audio_sha256=recording['audio']['sha256'],alignment_source='scotus_ctc',
        alignment_revision=entry['revision'],media_revision=entry['revision'])
    record.setdefault('description',f"<p>Oral argument for {html.escape(recording['case_name'])}, argued on {datetime.fromisoformat(date).strftime('%B %d, %Y')}.</p>")
    record.setdefault('description_source','oyez' if existing.get('source')=='oyez' or 'Facts of the case (from oyez.org)' in record.get('description','') else 'scotus')
    if record['description_source']=='scotus':record['description']=record['description'].replace('<p>Once a transcript is available on oyez.org, the recording and this description will be replaced by more detailed information.</p>','').strip()
    data.setdefault(term,{})[docket]=record
    return result

def get_from_alignment(dry_run=False):
    path=Path('data/case_data.json');data=json.loads(path.read_text())
    try:index,_=fetch_json(INDEX,524288)
    except requests.HTTPError as error:
        if dry_run:raise
        if error.response.status_code==404:return []
        log.exception('Alignment index unavailable; continuing with existing episodes and Oyez');return []
    except requests.RequestException:
        if dry_run:raise
        log.exception('Alignment index unavailable; continuing with existing episodes and Oyez');return []
    results=[]
    for entry in sorted(index.get('recordings',{}).values(),key=lambda e:e['argument_date']):
        if data.get(entry['term'],{}).get(entry['docket'],{}).get('alignment_revision')==entry['revision']:continue
        try:
            recording,raw=fetch_json(entry['url'])
            if hashlib.sha256(raw).hexdigest()!=entry['revision']:raise ValueError('Export checksum differs')
            result=apply_recording(data,entry,recording,dry_run)
            if result:
                results.append(result)
                if not dry_run:
                    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(data,indent=2));temporary.replace(path)
                    with open('commit_message.txt','a') as f:f.write(f"Alignment chapters for {entry['docket']}. ")
        except Exception:log.exception('Alignment import failed for %s; retaining existing episode',entry['recording_id'])
    return results

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--dry-run',action='store_true');args=parser.parse_args()
    print(json.dumps(get_from_alignment(args.dry_run),indent=2))
