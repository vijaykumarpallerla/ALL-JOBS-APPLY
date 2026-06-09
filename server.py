import os
import json
import subprocess
import uuid
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

local_appdata = os.getenv('LOCALAPPDATA', os.path.expanduser('~'))
kforce_dir = os.path.join(local_appdata, 'Kforce')
config_path = os.path.join(kforce_dir, 'rules.json')
resume_dir = os.path.join(kforce_dir, 'resumes')

os.makedirs(kforce_dir, exist_ok=True)
os.makedirs(resume_dir, exist_ok=True)

def load_rules():
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except: pass
    return []

def save_rules(rules):
    with open(config_path, 'w') as f:
        json.dump(rules, f, indent=4)

@app.route('/')
def index():
    rules = load_rules()
    return render_template('index.html', rules=rules)

@app.route('/save_rule', methods=['POST'])
def save_rule():
    data = dict(request.form)
    rules = load_rules()
    
    rule_id = data.get('id', '')
    if not rule_id:
        rule_id = str(uuid.uuid4())
        data['id'] = rule_id
        is_new = True
    else:
        is_new = False

    # Handle file upload
    if 'resume' in request.files and request.files['resume'].filename != '':
        file = request.files['resume']
        
        # Save in a subdirectory for this rule so the filename stays completely original
        rule_resume_dir = os.path.join(resume_dir, rule_id)
        os.makedirs(rule_resume_dir, exist_ok=True)
        
        filepath = os.path.join(rule_resume_dir, file.filename)
        file.save(filepath)
        data['resume_path'] = filepath
        data['resume_name'] = file.filename
    elif not is_new:
        # Keep existing resume
        for r in rules:
            if r['id'] == rule_id:
                data['resume_path'] = r.get('resume_path', '')
                data['resume_name'] = r.get('resume_name', '')
                break

    if is_new:
        rules.append(data)
    else:
        for i, r in enumerate(rules):
            if r['id'] == rule_id:
                rules[i] = data
                break
                
    save_rules(rules)
    return jsonify({"status": "success", "message": "Rule saved successfully!"})

@app.route('/delete_rule', methods=['POST'])
def delete_rule():
    rule_id = request.form.get('id')
    rules = [r for r in load_rules() if r['id'] != rule_id]
    save_rules(rules)
    return jsonify({"status": "success"})

@app.route('/start/<rule_id>', methods=['POST'])
def start_bot(rule_id):
    try:
        subprocess.Popen(["python", "apply.py", rule_id])
        return jsonify({"status": "success", "message": "Bot started in the background!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=200000)
