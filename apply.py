import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import base64
import os
import sys

# Suppress the annoying OSError from undetected_chromedriver's __del__ method
import logging
logging.getLogger().setLevel(logging.CRITICAL)
def suppress_del_error(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except OSError:
            pass
    return wrapper
uc.Chrome.__del__ = suppress_del_error(uc.Chrome.__del__)

def robust_type(wait, xpath, text, driver):
    try:
        element = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.5)
        # We use Javascript injection instead of send_keys.
        # This completely bypasses Windows OS restrictions, allowing it to work 100% perfectly even if the window is fully minimized!
        driver.execute_script(f"""
            var el = arguments[0];
            el.value = '{text}';
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            el.dispatchEvent(new Event('blur'));
        """, element)
        time.sleep(1) # Keep a small pause so it still looks paced out
    except Exception as e:
        print(f"Warning: Could not type into {xpath}. It may have changed.")

def apply_to_job(internal_job_id, config, driver):
    apply_page_url = f'https://www.kforce.com/Jobs/{internal_job_id}/ApplyOnline/'
    
    wait = WebDriverWait(driver, 15)
    
    try:
        print(f"Navigating to {apply_page_url}...")
        driver.get(apply_page_url)
        time.sleep(3) # Let Knockout.js initialize
        
        resume_path = config.get("resume_path", "")
        if not os.path.isabs(resume_path):
            resume_path = os.path.abspath(resume_path)
        
        print("Uploading Resume...")
        # Uploading file natively
        file_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
        file_input.send_keys(resume_path)
        
        # VERY IMPORTANT: KnockoutJS relies on the 'change' event to start the upload!
        driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", file_input)
        
        # Wait for Knockout to process the upload and get the green checkmark
        print("Waiting for AJAX resume upload to complete...")
        time.sleep(8)
        
        print("Filling personal details...")
        # Robust selectors that rely on placeholders, names, or types, making it very resilient to HTML changes
        robust_type(wait, "//input[translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='first name *' or contains(@name, 'first')]", config["first_name"], driver)
        robust_type(wait, "//input[translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='last name *' or contains(@name, 'last')]", config["last_name"], driver)
        robust_type(wait, "//input[contains(@placeholder, 'Primary Email') or contains(@name, 'email') and not(contains(@name, 'Verify'))]", config["email"], driver)
        robust_type(wait, "//input[contains(@placeholder, 'Verify') or contains(@name, 'Verify')]", config["email"], driver)
        # Ultra-flexible phone selector, must be VISIBLE
        try:
            phone_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[not(@type='hidden') and (contains(@type, 'tel') or contains(translate(@name, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'phone') or contains(translate(@id, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'phone') or contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'phone') or contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'phone'))]")))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", phone_input)
            time.sleep(0.5)
            # Use Javascript for phone too so it works when minimized!
            phone_text = config["phone"]
            driver.execute_script(f"""
                var el = arguments[0];
                el.value = '{phone_text}';
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                el.dispatchEvent(new Event('blur'));
            """, phone_input)
        except Exception as e:
            print(f"Warning: Could not type into phone field. Error: {e}")

        robust_type(wait, "//input[contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'zip') or contains(translate(@name, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'postal')]", config["zip"], driver)
        
        # Select state
        try:
            state_select = wait.until(EC.presence_of_element_located((By.XPATH, "//select[contains(translate(@name, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'state')]")))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", state_select)
            time.sleep(0.5)
            state_val = config["state"]
            driver.execute_script(f"""
                var el = arguments[0];
                el.value = '{state_val}';
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            """, state_select)
        except:
            pass

        # Select eligibility radio
        try:
            eligibility_value = config.get("eligibility", "AuthorizedForAny")
            if eligibility_value == "AuthorizedForAny":
                search_text = "for any employer"
            elif eligibility_value == "AuthorizedForPresentEmployer":
                search_text = "solely for my present employer"
            else:
                search_text = "require sponsorship"
                
            # Find the label that contains the text
            radio_xpath = f"//label[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{search_text}')]"
            
            eligibility_label = wait.until(EC.presence_of_element_located((By.XPATH, radio_xpath)))
            driver.execute_script("arguments[0].scrollIntoView(true);", eligibility_label)
            time.sleep(0.5)
            # Click the label to check the radio
            driver.execute_script("arguments[0].click();", eligibility_label)
            
            # Also dispatch a change event on the underlying radio input just in case Knockout needs it
            driver.execute_script('''
                var label = arguments[0];
                var input = label.querySelector("input[type='radio']");
                if (!input && label.getAttribute("for")) {
                    input = document.getElementById(label.getAttribute("for"));
                }
                if (input) {
                    input.checked = true;
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                }
            ''', eligibility_label)
        except Exception as e:
            print(f"Warning: Could not select eligibility radio. Error: {e}")

        print("Handling cookie banner if present...")
        try:
            cookie_btn = driver.find_element(By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]")
            cookie_btn.click()
            time.sleep(1)
        except:
            pass

        print("Submitting the application...")
        # Press submit button
        submit_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@id='SubmitButton'] | //button[@id='SubmitButton']")))
        print(f"Found submit button: {submit_btn.get_attribute('outerHTML')[:100]}...")
        driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
        time.sleep(1)
        
        # Click via Javascript directly to completely avoid ElementClickInterceptedException
        driver.execute_script("arguments[0].click();", submit_btn)
        
        print("Waiting 10 seconds for submission to process...")
        time.sleep(10)
        
        # Removed screenshot logic as requested

        
        if "Thank you for applying" in driver.page_source:
            print("\n=============================================")
            print("SUCCESS! The application has been confirmed.")
            print("You will receive your email now.")
            print("=============================================\n")
        else:
            print("Warning: Did not detect 'Thank you' text. The application may have failed validation.")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    import app
    import base64
    import os
    import json
    import sys
    import time
    
    # 1. Setup Rule
    rule_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not rule_id:
        print("Error: Please provide a rule_id")
        sys.exit(1)
        
    config = None
    config_path = os.path.join(os.getenv('LOCALAPPDATA', os.path.expanduser('~')), 'Kforce', 'rules.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                rules = json.load(f)
                for r in rules:
                    if r.get('id') == rule_id:
                        config = r
                        break
        except:
            pass
            
    if not config:
        print(f"Error: Rule {rule_id} not found.")
        sys.exit(1)
        
    keyword = config.get('keyword', 'AI Engineer')
    print(f"Fetching latest jobs from Kforce Azure Search with keyword: '{keyword}'...")
    app.fetch_kforce_jobs(keyword=keyword)
    
    # 2. Load Jobs.json
    try:
        local_appdata = os.getenv('LOCALAPPDATA', os.path.expanduser('~'))
        jobs_path = os.path.join(local_appdata, 'Kforce', 'Jobs.json')
        with open(jobs_path, "r", encoding="utf-8") as f:
            jobs = json.load(f)
    except Exception as e:
        print(f"Could not read Jobs.json: {e}")
        sys.exit(1)
        
    # 3. Load previously applied jobs to avoid duplicates
    local_appdata = os.getenv('LOCALAPPDATA', os.path.expanduser('~'))
    applied_log = os.path.join(local_appdata, 'Kforce', 'applied_jobs.txt')
    if os.path.exists(applied_log):
        with open(applied_log, "r") as f:
            applied_ids = set(f.read().splitlines())
    else:
        applied_ids = set()

    print(f"\nFound {len(jobs)} jobs in Jobs.json.")
    print("Starting automated application process...")
    
    import undetected_chromedriver as uc
    print("Launching silent browser window...")
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options, version_main=148)
    driver.minimize_window() # Users love minimizing, so let's keep it minimized!
    
    # 5. Loop and apply
    try:
        for job in jobs:
            base64_id = job["URL"].split("/")[-1]
            
            try:
                # Add padding to base64 string if necessary
                padding = '=' * (4 - len(base64_id) % 4)
                internal_id = base64.urlsafe_b64decode(base64_id + padding).decode('utf-8')
            except Exception as e:
                print(f"Could not decode ID {base64_id}: {e}")
                continue
                
            if internal_id in applied_ids:
                print(f"Skipping {internal_id} - Already applied.")
                continue
                
            print(f"\n[{job['Job number']}/{len(jobs)}] Now Applying to: {job['TITLE']} ({job['Job Type']})")
            print(f"Posted: {job['Date Posted']}")
            
            try:
                apply_to_job(internal_id, config, driver)
                # Mark as applied so we don't apply again in the future!
                with open(applied_log, "a") as f:
                    f.write(internal_id + "\n")
                    
                print("Successfully finished processing this job. Waiting 10 seconds before the next one...")
                time.sleep(10)
            except Exception as e:
                print(f"Failed to apply to {internal_id}: {e}")
                print("Continuing to the next job...")
                time.sleep(5)
    finally:
        print("\nAll jobs processed! Automated system complete. Closing browser.")
        driver.quit()
        
        # Start Vaco Automation in the same terminal
        try:
            import vaco_bot
            vaco_bot.run_vaco_automation(config)
        except Exception as e:
            print(f"Error starting Vaco automation: {e}")
