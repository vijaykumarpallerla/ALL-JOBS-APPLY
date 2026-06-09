import requests
from bs4 import BeautifulSoup
import os
import urllib.parse
import time
import json

def get_ordinal(n):
    ordinals = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 
                6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth"}
    return ordinals.get(n, f"{n}th")

def fetch_vaco_jobs(keyword):
    encoded_kw = urllib.parse.quote(keyword)
    url = f"https://jobs.vaco.com/api/requisitions/search?keywords={encoded_kw}"
    print("search keyword and URL")
    print(f"URL: {url}")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    try:
        response = session.get(url)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching Vaco jobs: {e}")
        return []
        
    soup = BeautifulSoup(response.text, 'html.parser')
    jobs = []
    
    table = soup.find('table', class_='job-search-results')
    if table:
        tbody = table.find('tbody')
        if tbody:
            for row in tbody.find_all('tr'):
                title_cell = row.find('td', class_='job-title')
                if title_cell and title_cell.find('a'):
                    title = title_cell.find('a').text.strip()
                    link = title_cell.find('a')['href'].strip()
                    # Only append if valid link
                    if link.startswith('http'):
                        jobs.append({"Title": title, "Link": link})
                        
    return jobs

def apply_to_vaco_job(job_url, config, session):
    fname = config.get("first_name", "")
    lname = config.get("last_name", "")
    email = config.get("email", "")
    resume_path = config.get("resume_path", "")
    
    # 1. GET request
    try:
        response = session.get(job_url)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to load job page: {e}")
        return False
        
    # 2. Fetch real CSRF token
    csrf_req = session.post("https://jobs.vaco.com/csrf-token", json={"decrypt": True, "token": None})
    real_token = csrf_req.text if csrf_req.status_code == 200 else None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    form = soup.find('form', id='tc-form')
    if not form:
        return False
        
    action_url = form.get('action')
    if not action_url:
        return False
        
    data = {}
    for input_tag in form.find_all('input', type='hidden'):
        name = input_tag.get('name')
        value = input_tag.get('value', '')
        if name:
            data[name] = value
            
    if real_token:
        data['_token'] = real_token
        
    data['fname'] = fname
    data['lname'] = lname
    data['email'] = email
    data['phoneNumber'] = config.get("phone", "")
    data['website'] = ''
    data['consent_yes'] = '1'
    
    if not os.path.exists(resume_path):
        print(f"Error: Resume not found at {resume_path}")
        return False
        
    print("applying")
    print(f"entering teh first name : {fname}")
    print(f"Last name : {lname}")
    print(f"email id : {email}")
    print(f"resume : {resume_path}")
    print("Submitting...")
    
    # 3. Submit
    session.headers.update({
        'Referer': job_url,
        'X-CSRF-TOKEN': data.get('_token', ''),
        'X-Requested-With': 'XMLHttpRequest'
    })
    
    try:
        with open(resume_path, 'rb') as f:
            files = {
                'localFile': (os.path.basename(resume_path), f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            }
            post_response = session.post(action_url, data=data, files=files)
            
        if post_response.status_code == 200:
            try:
                response_data = post_response.json()
                if response_data.get('tcSuccess') is True:
                    print("Success!")
                    return True
            except:
                if "Success!" in post_response.text:
                    print("Success!")
                    return True
        return False
    except Exception as e:
        print(f"Error during submission: {e}")
        return False

def run_vaco_automation(config):
    print("\napplying Vaco portal")
    
    keyword = config.get("keyword", "Java Developer")
    jobs = fetch_vaco_jobs(keyword)
    
    print(f"found {len(jobs)} jobs")
    
    local_appdata = os.getenv('LOCALAPPDATA', os.path.expanduser('~'))
    vaco_log = os.path.join(local_appdata, 'Kforce', 'vaco_applied_jobs.txt')
    
    if os.path.exists(vaco_log):
        with open(vaco_log, "r") as f:
            applied_urls = set(f.read().splitlines())
    else:
        applied_urls = set()
        
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0'
    })
    
    count = 1
    for job in jobs:
        link = job["Link"]
        if link in applied_urls:
            continue
            
        ordinal = get_ordinal(count)
        print(f"\n{ordinal} job URL : {link}")
        
        success = apply_to_vaco_job(link, config, session)
        if success:
            with open(vaco_log, "a") as f:
                f.write(link + "\n")
            time.sleep(5)
        else:
            print("Failed to apply.")
            
        count += 1
        
    print("\nAll Vaco jobs processed! Automated system complete.")
