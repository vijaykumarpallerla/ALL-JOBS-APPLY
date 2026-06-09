import urllib.request
import urllib.error
import json
import ssl
from datetime import datetime, timedelta, timezone

def fetch_kforce_jobs(keyword="AI Engineer"):
    search_service_url = "https://kforcewebeast.search.windows.net"
    api_key = "1603E4DC4C87A8E41D6BBDE4EEA4EFB7"
    api_version = "2020-06-30"  # Azure Search standard API version
    
    # Try different common index names
    index_candidates = ["kforcewebjobentity"]
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    successful_index = None
    raw_data = None

    for index_name in index_candidates:
        url = f"{search_service_url}/indexes/{index_name}/docs/search?api-version={api_version}"
        
        # Build payload with dynamic keyword
        payload = {
            "count": True,
            "search": keyword,
            "searchFields": "Title, Skills, Responsibilities",
            "select": "Id, Title, PostDate, TypeCode, City, State, Responsibilities, Skills",
            "top": 200  # Pull more to account for filtering
        }
        
        headers = {
            "Content-Type": "application/json",
            "api-key": api_key,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        
        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method="POST"
        )
        
        print(f"Testing Azure Search index: '{index_name}'...")
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                if response.status == 200:
                    raw_data = json.loads(response.read().decode('utf-8'))
                    successful_index = index_name
                    print(f"--> Success! Found index: '{index_name}'")
                    break
        except urllib.error.HTTPError as e:
            print(f"  HTTP Error {e.code} for '{index_name}': {e.reason}")
        except Exception as e:
            print(f"  Error for '{index_name}': {e}")
            
    if not successful_index or not raw_data:
        print("\nCould not fetch jobs directly. Attempting to list indexes...")
        # Try to list indexes to find the correct name
        list_url = f"{search_service_url}/indexes?api-version={api_version}"
        list_req = urllib.request.Request(
            list_url,
            headers={"api-key": api_key, "Content-Type": "application/json"},
            method="GET"
        )
        try:
            with urllib.request.urlopen(list_req, context=ctx, timeout=10) as response:
                indexes_info = json.loads(response.read().decode('utf-8'))
                index_names = [idx['name'] for idx in indexes_info.get('value', [])]
                print(f"Available indexes: {index_names}")
                if index_names:
                    # Retry search with the first found index
                    # (Code to retry here if needed)
                    pass
        except Exception as e:
            print(f"Could not list indexes: {e}")
        return

    # Process and save jobs
    jobs_list = raw_data.get('value', [])
    formatted_jobs = []
    
    print(f"\nProcessing {len(jobs_list)} jobs...")
    
    # Calculate today and yesterday
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    valid_dates = [now.strftime("%Y-%m-%d"), yesterday.strftime("%Y-%m-%d")]
    
    for idx, job in enumerate(jobs_list, 1):
        job_type = job.get('TypeCode', 'Unknown')
        post_date = job.get('PostDate', 'Unknown')
        
        # 1. Filter: Job Must be Contract
        if 'contract' not in job_type.lower():
            continue
            
        # 2. Filter: Job Must be Posted Today or Yesterday
        if post_date != 'Unknown':
            just_date = post_date.split('T')[0]
            if just_date not in valid_dates:
                continue
                
        job_id = job.get('Id')
        title = job.get('Title')
        
        # Build details URL in the standard format used by KForce:
        # e.g., https://www.kforce.com/find-work/search-jobs/#/detail/<job_id>
        # Note: Some job portals base64 encode or format the job ID. Let's provide a standard URL
        job_url = f"https://www.kforce.com/find-work/search-jobs/#/detail/{job_id}"
        
        # Combine Responsibilities and Skills as the Description
        resp = job.get('Responsibilities', '') or ''
        skills = job.get('Skills', '') or ''
        description = f"{resp}\n\nSkills:\n{skills}".strip()
        
        formatted_jobs.append({
            "Job number": idx,
            "TITLE": title,
            "Job Type": job_type,
            "Date Posted": post_date,
            "URL": job_url,
            "Description": description
        })
        
    # Write to Jobs.json
    import os
    local_appdata = os.getenv('LOCALAPPDATA', os.path.expanduser('~'))
    output_path = os.path.join(local_appdata, 'Kforce', 'Jobs.json')
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(formatted_jobs, f, indent=4)
        
    print(f"Successfully saved {len(formatted_jobs)} jobs matching criteria to {output_path}!")

if __name__ == "__main__":
    fetch_kforce_jobs()
