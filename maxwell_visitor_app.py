#!/usr/bin/env python3
"""
Maxwell Engineering Solutions - Visitor Management System
Run: python maxwell_visitor_app.py
Open: http://localhost:5000
Install: pip install flask qrcode pillow
"""

from flask import Flask, request, jsonify, redirect, session
import sqlite3, base64, io, threading, smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    import qrcode
    HAS_QR = True
except:
    HAS_QR = False

app = Flask(__name__)
app.secret_key = "maxwell2024secret"
DB = "maxwell_visitors.db"

SENDER_EMAIL    = "maxwell.visitors05@gmail.com"
SENDER_PASSWORD = "YOUR_GMAIL_APP_PASSWORD"
ADMIN_EMAIL     = "info@maxwells.in"
ADMIN_PIN       = "1234"

EMPLOYEE_EMAILS = {
    "Nishit Patel"        : "production@maxwells.in",
    "Vaibhav Desai"       : "qa@maxwells.in",
    "Vasant Sarla"        : "qc@maxwells.in",
    "Mohit Goswami"       : "head.hoa@maxwells.in",
    "Vrunda Thakkar"      : "hr1@maxwells.in",
    "Harshida Pandor"     : "hr2@maxwells.in",
    "Patel Pritesh"       : "maintenance@maxwells.in",
    "Parmar Romik"        : "accounts@maxwells.in",
    "Ajinkya Bapat"       : "purchase@maxwells.in",
    "Mayur Dod"           : "sales1@maxwells.in",
    "RajvinderKaur Hunda" : "Sales2@maxwells.in",
    "Krati Gupta"         : "cs@maxwells.in",
    "RAJKUMAR CHAUDHARY"  : "rajkumar@maxwells.in",
    "VINU CHAVDA"         : "vinu@maxwells.in",
    "PRABHAT SINGH KUMAR" : "ceo@maxwells.in",
    "POOJA LOKHANDE"      : "cfo@maxwells.in",
    "CHETNA BODKE"        : "marketing@maxwells.in",
}

DEPARTMENTS = {
    "Operation"  : ["Nishit Patel"],
    "QA"         : ["Vaibhav Desai"],
    "QC"         : ["Vasant Sarla"],
    "HR"         : ["Mohit Goswami", "Vrunda Thakkar", "Harshida Pandor"],
    "Maintenance": ["Patel Pritesh"],
    "Account"    : ["Parmar Romik"],
    "Purchase"   : ["Ajinkya Bapat"],
    "Marketing"  : ["Mayur Dod", "RajvinderKaur Hunda"],
    "Others"     : [],
}

FACTORY_DEPTS = {
    "Operation": ["Nishit Patel"],
    "QA"       : ["Vaibhav Desai"],
    "QC"       : ["Vasant Sarla"],
}

MANAGEMENT_LIST = [
    "RAJKUMAR CHAUDHARY", "VINU CHAVDA", "PRABHAT SINGH KUMAR",
    "POOJA LOKHANDE", "Krati Gupta", "CHETNA BODKE"
]

PASS_COLORS = {
    "Factory Visit": ("FFD700", "000000", "FACTORY"),
    "Staff Visit"  : ("1565C0", "FFFFFF", "STAFF"),
    "Management"   : ("2E7D32", "FFFFFF", "MANAGEMENT"),
}

DEFAULT_PHOTO = "data:image/svg+xml;base64," + base64.b64encode(
    b"<svg xmlns='http://www.w3.org/2000/svg' width='80' height='80'>"
    b"<circle cx='40' cy='40' r='40' fill='#e0e0e0'/>"
    b"<text x='40' y='50' font-family='Arial' font-size='32' fill='#999' text-anchor='middle'>?</text>"
    b"</svg>"
).decode()

LOGO_MW = "data:image/svg+xml;base64," + base64.b64encode(
    b"<svg width='80' height='80' xmlns='http://www.w3.org/2000/svg'>"
    b"<rect width='80' height='80' fill='white'/>"
    b"<circle cx='40' cy='40' r='36' fill='#1565C0'/>"
    b"<text x='40' y='52' font-family='Arial Black' font-size='26' font-weight='900' fill='white' text-anchor='middle'>MW</text>"
    b"</svg>"
).decode()

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS visitors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, phone TEXT, purpose TEXT, host_name TEXT,
        category TEXT, department TEXT, person_to_meet TEXT,
        photo TEXT, status TEXT DEFAULT 'pending',
        created_at TEXT, pass_number TEXT
    )""")
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def send_email(to_list, subject, body):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = ", ".join(to_list)
        msg.attach(MIMEText(body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(SENDER_EMAIL, SENDER_PASSWORD)
            s.sendmail(SENDER_EMAIL, to_list, msg.as_string())
    except Exception as e:
        print("Email error:", e)

def notify_new_visitor(v):
    dept = v["department"]
    recipients = [ADMIN_EMAIL]
    for emp in DEPARTMENTS.get(dept, []):
        email = EMPLOYEE_EMAILS.get(emp)
        if email and email not in recipients:
            recipients.append(email)
    person_email = EMPLOYEE_EMAILS.get(v["person_to_meet"])
    if person_email and person_email not in recipients:
        recipients.append(person_email)
    vid = str(v["id"])
    approve_url = "http://localhost:5000/action/" + vid + "/approve"
    reject_url  = "http://localhost:5000/action/" + vid + "/reject"
    body = (
        "<div style='font-family:Arial;max-width:600px;margin:auto;border:2px solid #1565C0;border-radius:10px;overflow:hidden'>"
        "<div style='background:#1565C0;color:white;padding:20px;text-align:center'><h2>Maxwell Engineering Solutions</h2><p>New Visitor Request</p></div>"
        "<div style='padding:20px'><table style='width:100%;border-collapse:collapse'>"
        "<tr><td style='padding:8px;font-weight:bold'>Name</td><td>" + str(v["name"]) + "</td></tr>"
        "<tr style='background:#f5f5f5'><td style='padding:8px;font-weight:bold'>Phone</td><td>" + str(v["phone"]) + "</td></tr>"
        "<tr><td style='padding:8px;font-weight:bold'>Host</td><td>" + str(v.get("host_name","")) + "</td></tr>"
        "<tr style='background:#f5f5f5'><td style='padding:8px;font-weight:bold'>Category</td><td>" + str(v["category"]) + "</td></tr>"
        "<tr><td style='padding:8px;font-weight:bold'>Department</td><td>" + str(v["department"]) + "</td></tr>"
        "<tr style='background:#f5f5f5'><td style='padding:8px;font-weight:bold'>Meeting</td><td>" + str(v["person_to_meet"]) + "</td></tr>"
        "<tr><td style='padding:8px;font-weight:bold'>Purpose</td><td>" + str(v["purpose"]) + "</td></tr>"
        "<tr style='background:#f5f5f5'><td style='padding:8px;font-weight:bold'>Time</td><td>" + str(v["created_at"]) + "</td></tr>"
        "</table>"
        "<div style='text-align:center;margin:25px 0'>"
        "<a href='" + approve_url + "' style='background:#2E7D32;color:white;padding:12px 30px;border-radius:5px;text-decoration:none;font-size:16px;margin:5px'>APPROVE</a>"
        "&nbsp;&nbsp;"
        "<a href='" + reject_url + "' style='background:#C62828;color:white;padding:12px 30px;border-radius:5px;text-decoration:none;font-size:16px;margin:5px'>REJECT</a>"
        "</div></div></div>"
    )
    threading.Thread(target=send_email, args=(recipients, "New Visitor: " + v["name"], body), daemon=True).start()

def make_qr(data):
    if not HAS_QR:
        return ""
    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

@app.route("/")
def index():
    depts_js   = str(DEPARTMENTS).replace("'", '"')
    factory_js = str(FACTORY_DEPTS).replace("'", '"')
    mgmt_js    = str(MANAGEMENT_LIST).replace("'", '"')

    page = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Maxwell - Visitor Management</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Arial,sans-serif;background:#f0f4f8}
.header{background:white;padding:12px 25px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 8px rgba(0,0,0,0.1);border-bottom:3px solid #1565C0}
.logo-box{display:flex;align-items:center;gap:10px}
.logo-sq{width:50px;height:50px;border-radius:10px;background:#1565C0;display:flex;align-items:center;justify-content:center;color:white;font-family:Arial Black;font-size:17px;font-weight:900}
.logo-text h2{color:#1565C0;font-size:17px;font-weight:900;letter-spacing:1px}
.logo-text p{color:#777;font-size:10px}
.hdr-title h1{color:#1565C0;font-size:17px;font-weight:900;text-align:center}
.hdr-title p{color:#777;font-size:11px;text-align:center}
.nav a{color:#1565C0;text-decoration:none;font-size:13px;padding:7px 15px;border:1.5px solid #1565C0;border-radius:6px;margin-left:6px;font-weight:600}
.nav a:hover{background:#1565C0;color:white}
.container{max-width:660px;margin:22px auto;padding:0 14px}
.card{background:white;border-radius:12px;padding:20px 22px;box-shadow:0 3px 10px rgba(0,0,0,0.07);margin-bottom:14px}
.section-title{font-size:14px;font-weight:700;color:#444;margin-bottom:15px}
.field-label{font-size:13px;font-weight:600;color:#555;margin-bottom:6px;display:block}
.req{color:#e53935}
input[type=text],input[type=tel],textarea{width:100%;padding:10px 13px;border:1.5px solid #ddd;border-radius:8px;font-size:14px;background:#fafafa;font-family:inherit;outline:none}
input:focus,textarea:focus{border-color:#1565C0;background:white}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:13px;margin-bottom:13px}
.row1{margin-bottom:13px}

/* Radio category chips */
.cat-group{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:5px}
.cat-chip input[type=radio]{display:none}
.cat-chip label{display:inline-block;padding:9px 20px;border-radius:25px;border:2px solid #ddd;font-size:13px;font-weight:600;cursor:pointer;color:#555;background:white;transition:0.2s}
.cat-chip input:checked + label{background:#1565C0;color:white;border-color:#1565C0}
.cat-chip label:hover{border-color:#1565C0;color:#1565C0}

/* Dept chips */
.dept-group{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:5px}
.dept-chip{padding:8px 16px;border-radius:20px;border:1.5px solid #ddd;font-size:13px;font-weight:600;cursor:pointer;color:#555;background:white;transition:0.2s}
.dept-chip:hover{border-color:#1565C0;color:#1565C0}
.dept-chip.selected{background:#1565C0;color:white;border-color:#1565C0}

/* Person chips */
.person-group{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:5px}
.person-chip{padding:8px 16px;border-radius:20px;border:1.5px solid #ddd;font-size:13px;font-weight:600;cursor:pointer;color:#555;background:white;transition:0.2s}
.person-chip:hover{border-color:#1565C0;color:#1565C0}
.person-chip.selected{background:#1565C0;color:white;border-color:#1565C0}

.hidden{display:none}
.camera-area{text-align:center;padding:8px 0}
#video{width:100%;max-width:360px;border-radius:8px;border:2px solid #ddd;display:none}
#photo-preview{width:100px;height:100px;border-radius:50%;object-fit:cover;border:3px solid #1565C0;display:none;margin:8px auto}
#ph-icon{font-size:60px;color:#ddd;margin:6px 0;display:block}
.btn{padding:9px 18px;border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;margin:3px}
.btn-blue{background:#1565C0;color:white}
.btn-green{background:#2E7D32;color:white}
.btn-red{background:#C62828;color:white}
.submit-btn{width:100%;padding:14px;font-size:15px;border-radius:10px;background:linear-gradient(135deg,#1565C0,#1976D2);color:white;border:none;cursor:pointer;font-weight:700;letter-spacing:1px;margin-top:4px}
.submit-btn:hover{opacity:0.92}
.alert{padding:11px 18px;border-radius:8px;margin-bottom:13px;font-size:14px;font-weight:500}
.alert-error{background:#ffebee;color:#C62828;border:1px solid #ef9a9a}
.submitted-msg{text-align:center;padding:30px}
.submitted-msg h2{color:#2E7D32;font-size:22px}
.submitted-msg p{color:#666;margin-top:8px;font-size:15px}
@media(max-width:560px){.row2{grid-template-columns:1fr}.header{flex-direction:column;gap:8px}}
</style>
</head>
<body>

<div class="header">
  <div class="logo-box">
    <div class="logo-sq">MW</div>
    <div class="logo-text">
      <h2>MAXWELL</h2>
      <p>ENGINEERING SOLUTIONS</p>
    </div>
  </div>
  <div class="hdr-title">
    <h1>Visitor Management System</h1>
    <p>Maxwell Engineering Solutions</p>
  </div>
  <div class="nav">
    <a href="/admin">Admin</a>
    <a href="/employee-login">Employee</a>
  </div>
</div>

<div class="container">
  <div id="alert-box"></div>

  <div id="form-section">

    <div class="card">
      <div class="section-title">Visitor Entry</div>

      <div class="row1">
        <label class="field-label">Name of Host</label>
        <input type="text" id="v-host" placeholder="Who are you visiting?">
      </div>

      <div class="row2">
        <div>
          <label class="field-label">Full Name <span class="req">*</span></label>
          <input type="text" id="v-name" placeholder="Enter full name">
        </div>
        <div>
          <label class="field-label">Phone Number <span class="req">*</span></label>
          <input type="tel" id="v-phone" placeholder="Mobile number">
        </div>
      </div>

      <div class="row1">
        <label class="field-label">Purpose of Visit <span class="req">*</span></label>
        <textarea id="v-purpose" rows="2" placeholder="Brief purpose of visit"></textarea>
      </div>
    </div>

    <div class="card">
      <div class="section-title">Visitor Category <span class="req">*</span></div>
      <div class="cat-group">
        <div class="cat-chip"><input type="radio" name="category" id="cat-factory" value="Factory Visit" onchange="onCat()"><label for="cat-factory">Factory Visit</label></div>
        <div class="cat-chip"><input type="radio" name="category" id="cat-staff" value="Staff Visit" onchange="onCat()"><label for="cat-staff">Staff Visit</label></div>
        <div class="cat-chip"><input type="radio" name="category" id="cat-mgmt" value="Management" onchange="onCat()"><label for="cat-mgmt">Management</label></div>
      </div>
    </div>

    <div class="card hidden" id="dept-card">
      <div class="section-title">Department <span class="req">*</span></div>
      <div class="dept-group" id="dept-group"></div>
    </div>

    <div class="card hidden" id="person-card">
      <div class="section-title">Person to Meet <span class="req">*</span></div>
      <div class="person-group" id="person-group"></div>
      <div id="others-input" class="hidden" style="margin-top:10px">
        <input type="text" id="v-others" placeholder="Enter person name">
      </div>
    </div>

    <div class="card">
      <div class="section-title">Photo</div>
      <div class="camera-area">
        <span id="ph-icon">&#128247;</span>
        <img id="photo-preview" src="" alt="Photo">
        <video id="video" autoplay playsinline></video>
        <canvas id="canvas" style="display:none"></canvas>
        <div style="margin-top:10px">
          <button class="btn btn-blue" onclick="startCam()">&#128247; Capture Photo</button>
          <button class="btn btn-green" id="cap-btn" onclick="capPhoto()" style="display:none">&#10003; Done</button>
          <button class="btn btn-red" id="ret-btn" onclick="retake()" style="display:none">&#8635; Retake</button>
        </div>
      </div>
    </div>

    <button class="submit-btn" onclick="submitForm()">SUBMIT</button>
  </div>

  <div id="submitted-section" class="hidden">
    <div class="card submitted-msg">
      <div style="font-size:55px">&#10003;</div>
      <h2>Request Submitted!</h2>
      <p>Your request has been sent for approval.<br>Visitor pass will be ready once approved.</p>
      <br>
      <button class="btn btn-blue" onclick="location.reload()">&#43; New Visitor</button>
    </div>
  </div>
</div>

<script>
var DEPTS   = DEPTS_JS;
var FACTORY = FACTORY_JS;
var MGMT    = MGMT_JS;
var photoData   = null;
var camStream   = null;
var selDept     = "";
var selPerson   = "";

function onCat() {
  var cat = document.querySelector('input[name="category"]:checked');
  if (!cat) return;
  var val = cat.value;

  selDept = ""; selPerson = "";
  document.getElementById('dept-card').classList.add('hidden');
  document.getElementById('person-card').classList.add('hidden');
  document.getElementById('dept-group').innerHTML = "";
  document.getElementById('person-group').innerHTML = "";

  if (val === "Factory Visit") {
    document.getElementById('dept-card').classList.remove('hidden');
    Object.keys(FACTORY).forEach(function(d) {
      var chip = document.createElement('div');
      chip.className = 'dept-chip';
      chip.textContent = d;
      chip.onclick = function() { selectDept(d, val); };
      document.getElementById('dept-group').appendChild(chip);
    });
  } else if (val === "Staff Visit") {
    document.getElementById('dept-card').classList.remove('hidden');
    Object.keys(DEPTS).forEach(function(d) {
      var chip = document.createElement('div');
      chip.className = 'dept-chip';
      chip.textContent = d;
      chip.onclick = function() { selectDept(d, val); };
      document.getElementById('dept-group').appendChild(chip);
    });
  } else if (val === "Management") {
    document.getElementById('person-card').classList.remove('hidden');
    document.getElementById('others-input').classList.add('hidden');
    showPersons(MGMT);
  }
}

function selectDept(dept, cat) {
  selDept = dept;
  selPerson = "";
  document.querySelectorAll('.dept-chip').forEach(function(c){ c.classList.remove('selected'); });
  event.target.classList.add('selected');
  document.getElementById('person-group').innerHTML = "";
  document.getElementById('others-input').classList.add('hidden');

  if (dept === "Others") {
    document.getElementById('person-card').classList.remove('hidden');
    document.getElementById('person-group').innerHTML = "";
    document.getElementById('others-input').classList.remove('hidden');
    return;
  }

  document.getElementById('person-card').classList.remove('hidden');
  var list = (cat === "Factory Visit") ? FACTORY[dept] : DEPTS[dept];
  if (list) showPersons(list);
}

function showPersons(list) {
  var pg = document.getElementById('person-group');
  pg.innerHTML = "";
  list.forEach(function(p) {
    var chip = document.createElement('div');
    chip.className = 'person-chip';
    chip.textContent = p;
    chip.onclick = function() {
      selPerson = p;
      document.querySelectorAll('.person-chip').forEach(function(c){ c.classList.remove('selected'); });
      chip.classList.add('selected');
    };
    pg.appendChild(chip);
  });
}

async function startCam() {
  try {
    camStream = await navigator.mediaDevices.getUserMedia({video:{facingMode:'user'}});
    document.getElementById('video').srcObject = camStream;
    document.getElementById('video').style.display = 'block';
    document.getElementById('ph-icon').style.display = 'none';
    document.getElementById('photo-preview').style.display = 'none';
    document.getElementById('cap-btn').style.display = '';
    document.getElementById('ret-btn').style.display = 'none';
  } catch(e) { alert('Camera access denied!'); }
}

function capPhoto() {
  var v = document.getElementById('video');
  var c = document.getElementById('canvas');
  c.width = v.videoWidth || 320; c.height = v.videoHeight || 320;
  c.getContext('2d').drawImage(v, 0, 0);
  photoData = c.toDataURL('image/jpeg', 0.8);
  document.getElementById('photo-preview').src = photoData;
  document.getElementById('photo-preview').style.display = 'block';
  document.getElementById('video').style.display = 'none';
  document.getElementById('cap-btn').style.display = 'none';
  document.getElementById('ret-btn').style.display = '';
  if (camStream) camStream.getTracks().forEach(function(t){ t.stop(); });
}

function retake() {
  photoData = null;
  document.getElementById('photo-preview').style.display = 'none';
  document.getElementById('ret-btn').style.display = 'none';
  document.getElementById('ph-icon').style.display = 'block';
  startCam();
}

function showAlert(msg) {
  document.getElementById('alert-box').innerHTML = '<div class="alert alert-error">' + msg + '</div>';
  setTimeout(function(){ document.getElementById('alert-box').innerHTML=''; }, 5000);
}

async function submitForm() {
  var name    = document.getElementById('v-name').value.trim();
  var phone   = document.getElementById('v-phone').value.trim();
  var purpose = document.getElementById('v-purpose').value.trim();
  var host    = document.getElementById('v-host').value.trim();
  var catEl   = document.querySelector('input[name="category"]:checked');
  var cat     = catEl ? catEl.value : "";

  var dept   = selDept || "Management";
  var person = selPerson;

  if (dept === "Others") {
    person = document.getElementById('v-others').value.trim();
  }

  if (!name)    { showAlert('Please enter visitor name!'); return; }
  if (!phone)   { showAlert('Please enter phone number!'); return; }
  if (!purpose) { showAlert('Please enter purpose of visit!'); return; }
  if (!cat)     { showAlert('Please select visitor category!'); return; }
  if (!person)  { showAlert('Please select person to meet!'); return; }

  try {
    var res = await fetch('/api/visitor', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        name:name, phone:phone, purpose:purpose, host_name:host,
        category:cat, department:dept, person_to_meet:person, photo:photoData
      })
    });
    var data = await res.json();
    if (data.success) {
      document.getElementById('form-section').classList.add('hidden');
      document.getElementById('submitted-section').classList.remove('hidden');
    } else {
      showAlert('Error: ' + (data.error || 'Unknown error'));
    }
  } catch(e) {
    showAlert('Server error! Make sure app is running.');
  }
}
</script>
</body>
</html>"""

    page = page.replace("DEPTS_JS", depts_js)
    page = page.replace("FACTORY_JS", factory_js)
    page = page.replace("MGMT_JS", mgmt_js)
    return page


@app.route("/api/visitor", methods=["POST"])
def create_visitor():
    data = request.get_json()
    now = datetime.now().strftime("%d-%m-%Y %H:%M")
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM visitors")
    count = c.fetchone()[0] + 1
    pass_num = "MW-" + datetime.now().strftime("%Y%m%d") + "-" + str(count).zfill(4)
    c.execute(
        "INSERT INTO visitors (name,phone,purpose,host_name,category,department,person_to_meet,photo,created_at,pass_number) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (data.get("name"), data.get("phone"), data.get("purpose"), data.get("host_name"),
         data.get("category"), data.get("department"), data.get("person_to_meet"),
         data.get("photo"), now, pass_num)
    )
    vid = c.lastrowid
    conn.commit()
    v = dict(conn.execute("SELECT * FROM visitors WHERE id=?", (vid,)).fetchone())
    conn.close()
    notify_new_visitor(v)
    return jsonify({"success": True, "id": vid})


@app.route("/action/<int:vid>/<action>")
def do_action(vid, action):
    if action not in ("approve", "reject"):
        return "Invalid", 400
    conn = get_db()
    now = datetime.now().strftime("%d-%m-%Y %H:%M")
    conn.execute("UPDATE visitors SET status=? WHERE id=?", (action + "d", vid))
    conn.commit()
    conn.close()
    if "application/json" in request.headers.get("Accept", ""):
        return jsonify({"success": True, "message": "Visitor " + action + "d"})
    return (
        "<h2 style='text-align:center;margin-top:80px;font-family:Arial;color:#1565C0'>"
        "Visitor " + action.title() + "d!<br><br>"
        "<a href='/admin'>Admin Panel</a> &nbsp;|&nbsp; "
        "<a href='/pass/" + str(vid) + "'>View Pass</a></h2>"
    )


@app.route("/pass/<int:vid>")
def show_pass(vid):
    conn = get_db()
    row = conn.execute("SELECT * FROM visitors WHERE id=?", (vid,)).fetchone()
    conn.close()
    if not row:
        return "Not found", 404
    v = dict(row)
    if v["status"] != "approved":
        return (
            "<h2 style='text-align:center;margin-top:80px;font-family:Arial;color:#C62828'>"
            "Pass not available. Visitor must be approved first.<br><br>"
            "<a href='/admin' style='color:#1565C0'>Admin Panel</a></h2>"
        )
    bg, fg, label = PASS_COLORS.get(v["category"], ("1565C0", "FFFFFF", "VISITOR"))
    photo = v.get("photo") or DEFAULT_PHOTO
    qr = make_qr("Maxwell\nName: " + v["name"] + "\nPass: " + v["pass_number"] + "\nTime: " + v["created_at"])
    qr_img = '<img src="data:image/png;base64,' + qr + '" width="90">' if qr else ""
    page = (
        "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Visitor Pass</title>"
        "<style>body{font-family:Arial;background:#f0f0f0;display:flex;justify-content:center;padding:30px;flex-direction:column;align-items:center}"
        ".pass{width:370px;border-radius:14px;overflow:hidden;box-shadow:0 8px 25px rgba(0,0,0,0.2)}"
        ".ph{padding:15px 20px;display:flex;justify-content:space-between;align-items:center;background:#" + bg + ";color:#" + fg + "}"
        ".pb{background:white;padding:20px}.pf{background:#f5f5f5;text-align:center;padding:10px;font-size:11px;color:#888}"
        ".pp{width:78px;height:78px;border-radius:50%;object-fit:cover;border:3px solid white}"
        ".il{font-size:11px;color:#888;text-transform:uppercase;margin-bottom:2px}.iv{font-size:14px;font-weight:600;color:#222;margin-bottom:10px}"
        ".appr{background:#E8F5E9;color:#2E7D32;text-align:center;padding:8px;border-radius:5px;font-weight:700;margin-top:10px}"
        ".btns{margin-top:20px;text-align:center}"
        ".btns button{padding:10px 20px;margin:5px;border:none;border-radius:7px;cursor:pointer;font-size:14px;font-weight:600}"
        "@media print{body{background:white;padding:0}.btns{display:none}}</style></head><body>"
        "<div class='pass'>"
        "<div class='ph'>"
        "<div style='width:55px;height:55px;border-radius:10px;background:rgba(255,255,255,0.25);display:flex;align-items:center;justify-content:center;font-family:Arial Black;font-size:18px;font-weight:900;color:#" + fg + "'>MW</div>"
        "<div style='text-align:right'><div style='font-size:20px;font-weight:900'>" + label + "</div>"
        "<div style='font-size:12px;opacity:0.8'>" + str(v["pass_number"]) + "</div></div></div>"
        "<div class='pb'>"
        "<div style='display:flex;align-items:center;gap:14px;margin-bottom:18px'>"
        "<img src='" + photo + "' class='pp'>"
        "<div><div style='font-size:19px;font-weight:900;color:#1565C0'>" + str(v["name"]) + "</div>"
        "<div style='font-size:12px;color:#666'>" + str(v["category"]) + "</div></div></div>"
        "<hr style='border:none;border-top:1px solid #eee;margin-bottom:14px'>"
        "<div class='il'>Department</div><div class='iv'>" + str(v["department"]) + "</div>"
        "<div class='il'>Person to Meet</div><div class='iv'>" + str(v["person_to_meet"]) + "</div>"
        "<div class='il'>Purpose</div><div class='iv'>" + str(v["purpose"]) + "</div>"
        "<div class='il'>Date &amp; Time</div><div class='iv'>" + str(v["created_at"]) + "</div>"
        "<div style='text-align:center;margin-top:12px'>" + qr_img + "<div style='font-size:10px;color:#999;margin-top:3px'>Scan to verify</div></div>"
        "<div class='appr'>&#10003; APPROVED</div></div>"
        "<div class='pf'>Maxwell Engineering Solutions | Visitor Management System</div></div>"
        "<div class='btns'>"
        "<button onclick='window.print()' style='background:#1565C0;color:white'>Print Pass</button>"
        "<button onclick='window.close()' style='background:#666;color:white'>Close</button>"
        "</div>"
        "<script>setTimeout(function(){window.print();},600);</script>"
        "</body></html>"
    )
    return page


@app.route("/admin", methods=["GET"])
def admin():
    if not session.get("admin_ok"):
        return admin_login_page("")
    tab = request.args.get("tab", "pending")
    conn = get_db()
    if tab == "all":
        visitors = [dict(r) for r in conn.execute("SELECT * FROM visitors ORDER BY id DESC").fetchall()]
    else:
        visitors = [dict(r) for r in conn.execute("SELECT * FROM visitors WHERE status=? ORDER BY id DESC", (tab,)).fetchall()]
    counts = {}
    for r in conn.execute("SELECT status, COUNT(*) as cnt FROM visitors GROUP BY status").fetchall():
        counts[r["status"]] = r["cnt"]
    conn.close()
    pc = counts.get("pending", 0)
    ac = counts.get("approved", 0)
    rc = counts.get("rejected", 0)

    rows = ""
    for v in visitors:
        bc = "pending" if v["status"] == "pending" else ("approved" if v["status"] == "approved" else "rejected")
        photo = v["photo"] if v["photo"] else DEFAULT_PHOTO
        ab = ""
        if v["status"] == "pending":
            ab += '<button class="btn ba" onclick="act(' + str(v["id"]) + ",'approve'" + ')">&#10003; Approve</button>'
            ab += '<button class="btn br" onclick="act(' + str(v["id"]) + ",'reject'" + ')">&#10005; Reject</button>'
        ab += '<button class="btn bp" onclick="window.open(\'/pass/' + str(v["id"]) + '\')">Pass</button>'
        rows += (
            "<tr>"
            "<td><img src='" + photo + "' style='width:42px;height:42px;border-radius:50%;object-fit:cover;border:2px solid #ddd'></td>"
            "<td><strong>" + str(v["name"]) + "</strong></td>"
            "<td>" + str(v["phone"]) + "</td>"
            "<td>" + str(v["category"]) + "</td>"
            "<td>" + str(v["department"]) + "</td>"
            "<td>" + str(v["person_to_meet"]) + "</td>"
            "<td style='font-size:11px'>" + str(v["created_at"]) + "</td>"
            "<td><span class='badge " + bc + "'>" + v["status"].upper() + "</span></td>"
            "<td>" + ab + "</td>"
            "</tr>"
        )
    if not rows:
        rows = '<tr><td colspan="9" style="text-align:center;padding:25px;color:#999">No records</td></tr>'

    tab_a = {"pending":"","approved":"","rejected":"","all":""}
    tab_a[tab] = "active"

    return (
        "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Maxwell Admin</title>"
        "<style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:Arial;background:#f0f4f8}"
        ".header{background:#1565C0;color:white;padding:13px 25px;display:flex;justify-content:space-between;align-items:center}"
        ".header h1{font-size:18px}"
        ".header a{color:white;text-decoration:none;background:rgba(255,255,255,0.2);padding:7px 13px;border-radius:5px;font-size:13px;margin-left:7px}"
        ".container{max-width:1100px;margin:20px auto;padding:0 15px}"
        ".stats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:20px}"
        ".stat{background:white;border-radius:9px;padding:18px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.07)}"
        ".stat-n{font-size:34px;font-weight:900}.stat-l{font-size:12px;color:#666;margin-top:4px}"
        ".pend{color:#F57F17}.appr{color:#2E7D32}.reje{color:#C62828}"
        ".tabs{display:flex;gap:4px;margin-bottom:18px}"
        ".tab{padding:9px 18px;border:none;border-radius:7px 7px 0 0;cursor:pointer;font-weight:600;font-size:13px;background:#ddd;color:#555}"
        ".tab.active{background:white;color:#1565C0}"
        ".card{background:white;border-radius:9px;padding:18px;box-shadow:0 2px 8px rgba(0,0,0,0.07);overflow-x:auto}"
        "table{width:100%;border-collapse:collapse;min-width:850px}"
        "th{background:#1565C0;color:white;padding:11px;text-align:left;font-size:12px}"
        "td{padding:10px;border-bottom:1px solid #eee;font-size:13px;vertical-align:middle}"
        "tr:hover td{background:#f9f9f9}"
        ".badge{display:inline-block;padding:3px 9px;border-radius:11px;font-size:11px;font-weight:700}"
        ".badge.pending{background:#FFF8E1;color:#F57F17}"
        ".badge.approved{background:#E8F5E9;color:#2E7D32}"
        ".badge.rejected{background:#FFEBEE;color:#C62828}"
        ".btn{padding:5px 11px;border:none;border-radius:5px;cursor:pointer;font-size:12px;font-weight:600;margin:2px}"
        ".ba{background:#2E7D32;color:white}.br{background:#C62828;color:white}.bp{background:#1565C0;color:white}"
        "</style></head><body>"
        "<div class='header'><h1>Maxwell Admin Panel</h1>"
        "<div><a href='/'>Visitor Form</a><a href='/admin-logout'>Logout</a></div></div>"
        "<div class='container'>"
        "<div class='stats'>"
        "<div class='stat'><div class='stat-n pend'>" + str(pc) + "</div><div class='stat-l'>Pending</div></div>"
        "<div class='stat'><div class='stat-n appr'>" + str(ac) + "</div><div class='stat-l'>Approved</div></div>"
        "<div class='stat'><div class='stat-n reje'>" + str(rc) + "</div><div class='stat-l'>Rejected</div></div>"
        "</div>"
        "<div class='tabs'>"
        "<button class='tab " + tab_a["pending"] + "' onclick=\"location='?tab=pending'\">Pending (" + str(pc) + ")</button>"
        "<button class='tab " + tab_a["approved"] + "' onclick=\"location='?tab=approved'\">Approved</button>"
        "<button class='tab " + tab_a["rejected"] + "' onclick=\"location='?tab=rejected'\">Rejected</button>"
        "<button class='tab " + tab_a["all"] + "' onclick=\"location='?tab=all'\">All</button>"
        "</div>"
        "<div class='card'><table>"
        "<tr><th>Photo</th><th>Name</th><th>Phone</th><th>Category</th><th>Dept</th><th>Meeting</th><th>Time</th><th>Status</th><th>Action</th></tr>"
        + rows +
        "</table></div></div>"
        "<script>async function act(id,action){"
        "if(!confirm(action+' this visitor?'))return;"
        "var r=await fetch('/action/'+id+'/'+action,{headers:{'Accept':'application/json'}});"
        "var d=await r.json();"
        "if(action==='approve'){window.open('/pass/'+id);}"
        "location.reload();}"
        "</script></body></html>"
    )


def admin_login_page(err):
    return (
        "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Admin Login</title>"
        "<style>body{font-family:Arial;background:#f0f4f8}"
        ".header{background:#1565C0;color:white;padding:13px 25px}"
        ".box{max-width:380px;margin:70px auto;background:white;padding:38px;border-radius:13px;box-shadow:0 5px 18px rgba(0,0,0,0.1);text-align:center}"
        ".box h2{color:#1565C0;margin-bottom:22px}"
        "input{width:100%;padding:11px;border:2px solid #e0e0e0;border-radius:7px;font-size:15px;margin-bottom:14px}"
        "input:focus{outline:none;border-color:#1565C0}"
        "button{width:100%;padding:12px;background:#1565C0;color:white;border:none;border-radius:7px;font-size:15px;font-weight:700;cursor:pointer}"
        ".err{color:red;font-size:13px;margin-top:8px}"
        "a{display:block;margin-top:13px;color:#1565C0;font-size:13px}"
        "</style></head><body>"
        "<div class='header'><h1>Maxwell Engineering Solutions</h1></div>"
        "<div class='box'><h2>Admin Login</h2>"
        "<form method='POST' action='/admin-login'>"
        "<input type='password' name='pin' placeholder='Enter Admin PIN (1234)'>"
        "<button type='submit'>LOGIN</button></form>"
        + ("<p class='err'>" + err + "</p>" if err else "") +
        "<a href='/'>Back to Visitor Form</a></div></body></html>"
    )


@app.route("/admin-login", methods=["POST"])
def admin_login():
    if request.form.get("pin", "") == ADMIN_PIN:
        session["admin_ok"] = True
        return redirect("/admin")
    return admin_login_page("Wrong PIN! Try again.")


@app.route("/admin-logout")
def admin_logout():
    session.clear()
    return redirect("/admin")


@app.route("/employee-login", methods=["GET", "POST"])
def employee_login():
    err = ""
    if request.method == "POST":
        email    = request.form.get("email", "").lower().strip()
        password = request.form.get("password", "").strip()
        emp_map  = {v.lower(): k for k, v in EMPLOYEE_EMAILS.items()}
        if email in emp_map:
            emp_name = emp_map[email]
            if password == emp_name:
                session["emp_name"] = emp_name
                return redirect("/employee-dashboard")
            else:
                err = "Wrong password! Password is your full name."
        else:
            err = "Email not found. Use your official Maxwell email."
    return (
        "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Employee Login</title>"
        "<style>body{font-family:Arial;background:#f0f4f8}"
        ".header{background:#1565C0;color:white;padding:13px 25px}"
        ".box{max-width:400px;margin:60px auto;background:white;padding:38px;border-radius:13px;box-shadow:0 5px 18px rgba(0,0,0,0.1)}"
        ".box h2{color:#1565C0;text-align:center;margin-bottom:22px}"
        "label{display:block;font-size:13px;font-weight:600;color:#444;margin-bottom:5px;margin-top:14px}"
        "input{width:100%;padding:11px;border:2px solid #e0e0e0;border-radius:7px;font-size:14px}"
        "input:focus{outline:none;border-color:#1565C0}"
        "button{width:100%;margin-top:18px;padding:12px;background:#1565C0;color:white;border:none;border-radius:7px;font-size:15px;font-weight:700;cursor:pointer}"
        ".err{color:red;font-size:13px;margin-top:8px;text-align:center}"
        "a{display:block;text-align:center;margin-top:13px;color:#1565C0;font-size:13px}"
        "</style></head><body>"
        "<div class='header'><h1>Maxwell Engineering Solutions</h1></div>"
        "<div class='box'><h2>Employee Login</h2>"
        "<form method='POST'>"
        "<label>Company Email</label><input type='email' name='email' placeholder='yourname@maxwells.in' required>"
        "<label>Password</label><input type='password' name='password' placeholder='Your full name as password' required>"
        "<button type='submit'>LOGIN</button></form>"
        + ("<p class='err'>" + err + "</p>" if err else "") +
        "<a href='/'>Back to Visitor Form</a></div></body></html>"
    )


@app.route("/employee-dashboard")
def employee_dashboard():
    if not session.get("emp_name"):
        return redirect("/employee-login")
    name = session["emp_name"]
    conn = get_db()
    visitors = [dict(r) for r in conn.execute(
        "SELECT * FROM visitors WHERE person_to_meet=? ORDER BY id DESC", (name,)
    ).fetchall()]
    conn.close()

    rows = ""
    for v in visitors:
        bc = "pending" if v["status"] == "pending" else ("approved" if v["status"] == "approved" else "rejected")
        ab = ""
        if v["status"] == "pending":
            ab += '<button class="btn ba" onclick="act(' + str(v["id"]) + ",'approve'" + ')">&#10003; Approve</button>'
            ab += '<button class="btn br" onclick="act(' + str(v["id"]) + ",'reject'" + ')">&#10005; Reject</button>'
        else:
            ab = "-"
        rows += (
            "<tr>"
            "<td><strong>" + str(v["name"]) + "</strong></td>"
            "<td>" + str(v["phone"]) + "</td>"
            "<td>" + str(v["purpose"]) + "</td>"
            "<td>" + str(v["department"]) + "</td>"
            "<td style='font-size:11px'>" + str(v["created_at"]) + "</td>"
            "<td><span class='badge " + bc + "'>" + v["status"].upper() + "</span></td>"
            "<td>" + ab + "</td>"
            "</tr>"
        )
    if not rows:
        rows = '<tr><td colspan="7" style="text-align:center;padding:20px;color:#999">No visitor requests</td></tr>'

    return (
        "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Employee Dashboard</title>"
        "<style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:Arial;background:#f0f4f8}"
        ".header{background:#1565C0;color:white;padding:13px 25px;display:flex;justify-content:space-between;align-items:center}"
        ".header a{color:white;text-decoration:none;background:rgba(255,255,255,0.2);padding:7px 13px;border-radius:5px;font-size:13px;margin-left:7px}"
        ".container{max-width:900px;margin:20px auto;padding:0 15px}"
        ".card{background:white;border-radius:9px;padding:18px;box-shadow:0 2px 8px rgba(0,0,0,0.07);overflow-x:auto}"
        ".card h3{color:#1565C0;margin-bottom:14px}"
        "table{width:100%;border-collapse:collapse;min-width:650px}"
        "th{background:#1565C0;color:white;padding:10px;font-size:12px;text-align:left}"
        "td{padding:10px;border-bottom:1px solid #eee;font-size:13px;vertical-align:middle}"
        ".badge{display:inline-block;padding:3px 9px;border-radius:11px;font-size:11px;font-weight:700}"
        ".badge.pending{background:#FFF8E1;color:#F57F17}"
        ".badge.approved{background:#E8F5E9;color:#2E7D32}"
        ".badge.rejected{background:#FFEBEE;color:#C62828}"
        ".btn{padding:5px 11px;border:none;border-radius:5px;cursor:pointer;font-size:12px;font-weight:600;margin:2px}"
        ".ba{background:#2E7D32;color:white}.br{background:#C62828;color:white}"
        "</style></head><body>"
        "<div class='header'><h1>" + name + " - Dashboard</h1>"
        "<div><a href='/'>Visitor Form</a><a href='/employee-logout'>Logout</a></div></div>"
        "<div class='container'><div class='card'>"
        "<h3>Visitor Requests for You</h3>"
        "<table><tr><th>Name</th><th>Phone</th><th>Purpose</th><th>Dept</th><th>Time</th><th>Status</th><th>Action</th></tr>"
        + rows +
        "</table></div></div>"
        "<script>async function act(id,action){"
        "if(!confirm(action+' this visitor?'))return;"
        "var r=await fetch('/action/'+id+'/'+action,{headers:{'Accept':'application/json'}});"
        "var d=await r.json();"
        "if(action==='approve'){window.open('/pass/'+id);}"
        "location.reload();}"
        "</script></body></html>"
    )


@app.route("/employee-logout")
def employee_logout():
    session.clear()
    return redirect("/employee-login")


if __name__ == "__main__":
    init_db()
    print("\n" + "="*50)
    print("  Maxwell Engineering Solutions")
    print("  Visitor Management System")
    print("="*50)
    print("  App:    http://localhost:5000")
    print("  Admin:  http://localhost:5000/admin  PIN: 1234")
    print("="*50 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
