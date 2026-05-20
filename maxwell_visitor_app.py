#!/usr/bin/env python3
"""
Maxwell Engineering Solutions - Visitor Management System v2.0
"""

from flask import Flask, request, jsonify, redirect, session, send_file
import sqlite3, base64, io, threading, os, secrets
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

try:
    import qrcode
    HAS_QR = True
except:
    HAS_QR = False

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    HAS_EXCEL = True
except:
    HAS_EXCEL = False

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    HAS_SCHEDULER = True
except:
    HAS_SCHEDULER = False

app = Flask(__name__)
app.secret_key = "maxwell2024secret"
DB = "maxwell_visitors.db"

SENDER_EMAIL    = os.environ.get("SENDER_EMAIL", "abc81a001@smtp-brevo.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "xsmtpsib-0d9349ff85dcbcb8ffc1ab463f99e1c5e11f780be1e91a91a129f70f6c1ec28d-FXgz0FhVSKSiVpvG")
ADMIN_EMAIL     = os.environ.get("ADMIN_EMAIL", "info@maxwells.in")
ADMIN_PIN       = os.environ.get("ADMIN_PIN", "1234")
PANTRY_EMAIL    = os.environ.get("PANTRY_EMAIL", "maxwellvisitor05@gmail.com")
PANTRY_PASSWORD = os.environ.get("PANTRY_PASSWORD", "MaxwellPantry2024")
HOST_NOTIFY_EMAIL = os.environ.get("HOST_NOTIFY_EMAIL", "hr1@maxwells.in")

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

DRINKS_MENU = ["Water", "Tea", "Coffee", "Green Tea", "Black Coffee", "Juice", "Other"]

DEFAULT_PHOTO = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHdpZHRoPSc4MCcgaGVpZ2h0PSc4MCc+PGNpcmNsZSBjeD0nNDAnIGN5PSc0MCcgcj0nNDAnIGZpbGw9JyNlMGUwZTAnLz48dGV4dCB4PSc0MCcgeT0nNTAnIGZvbnQtZmFtaWx5PSdBcmlhbCcgZm9udC1zaXplPSczMicgZmlsbD0nIzk5OScgdGV4dC1hbmNob3I9J21pZGRsZSc+PzwvdGV4dD48L3N2Zz4="

# ── DATABASE ──────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS visitors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, phone TEXT, purpose TEXT, host_name TEXT,
        category TEXT, department TEXT, person_to_meet TEXT,
        photo TEXT, status TEXT DEFAULT 'pending',
        created_at TEXT, checkout_at TEXT, pass_number TEXT,
        advance_token TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS pantry_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        visitor_id INTEGER, visitor_name TEXT, person_to_meet TEXT,
        drink TEXT, snacks TEXT, quantity INTEGER, note TEXT,
        order_type TEXT DEFAULT 'drink',
        status TEXT DEFAULT 'pending',
        created_at TEXT, delivered_at TEXT, timer_start TEXT
    )""")
    for col in ["checkout_at", "advance_token"]:
        try: conn.execute(f"ALTER TABLE visitors ADD COLUMN {col} TEXT")
        except: pass
    for col in ["snacks TEXT", "order_type TEXT DEFAULT 'drink'"]:
        try: conn.execute(f"ALTER TABLE pantry_orders ADD COLUMN {col}")
        except: pass
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

# ── EMAIL ─────────────────────────────────────────────────
def send_email(to_list, subject, body):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = SENDER_EMAIL
        msg["To"]      = ", ".join(to_list)
        msg.attach(MIMEText(body, "html"))
        with smtplib.SMTP("smtp-relay.brevo.com", 2525) as s:
            s.starttls()
            s.login(SENDER_EMAIL, SENDER_PASSWORD)
            s.sendmail(SENDER_EMAIL, to_list, msg.as_string())
            print("Email sent to:", to_list)
    except Exception as e:
        print("Email error:", e)

def notify_new_visitor(v):
    """Visitor submit thaay - Admin + Host ne notification"""
    recipients = [ADMIN_EMAIL]
    person_email = EMPLOYEE_EMAILS.get(v["person_to_meet"])
    if person_email and person_email not in recipients:
        recipients.append(person_email)
    vid = str(v["id"])
    body = (
        "<div style='font-family:Arial;max-width:600px;margin:auto;border:2px solid #1565C0;border-radius:10px;overflow:hidden'>"
        "<div style='background:#1565C0;color:white;padding:20px;text-align:center'><h2>Maxwell Engineering Solutions</h2><p>New Visitor Request</p></div>"
        "<div style='padding:20px'><table style='width:100%;border-collapse:collapse'>"
        "<tr><td style='padding:8px;font-weight:bold'>Name</td><td>" + str(v["name"]) + "</td></tr>"
        "<tr style='background:#f5f5f5'><td style='padding:8px;font-weight:bold'>Phone</td><td>" + str(v["phone"]) + "</td></tr>"
        "<tr><td style='padding:8px;font-weight:bold'>Department</td><td>" + str(v["department"]) + "</td></tr>"
        "<tr style='background:#f5f5f5'><td style='padding:8px;font-weight:bold'>Meeting</td><td>" + str(v["person_to_meet"]) + "</td></tr>"
        "<tr><td style='padding:8px;font-weight:bold'>Purpose</td><td>" + str(v["purpose"]) + "</td></tr>"
        "<tr style='background:#f5f5f5'><td style='padding:8px;font-weight:bold'>Time</td><td>" + str(v["created_at"]) + "</td></tr>"
        "</table>"
        "<div style='text-align:center;margin:25px 0'>"
        "<a href='https://maxwell-visitor-app-2.onrender.com/action/" + vid + "/approve' style='background:#2E7D32;color:white;padding:12px 30px;border-radius:5px;text-decoration:none;font-size:16px;margin:5px'>APPROVE</a>"
        "&nbsp;&nbsp;"
        "<a href='https://maxwell-visitor-app-2.onrender.com/action/" + vid + "/reject' style='background:#C62828;color:white;padding:12px 30px;border-radius:5px;text-decoration:none;font-size:16px;margin:5px'>REJECT</a>"
        "</div></div></div>"
    )
    threading.Thread(target=send_email, args=(recipients, "New Visitor: " + str(v["name"]), body), daemon=True).start()

def notify_approved(v, now):
    """Guest approved - Host + Admin + Pantry ne notification"""
    person_email = EMPLOYEE_EMAILS.get(v["person_to_meet"])
    
    # Host + Admin
    host_recipients = [ADMIN_EMAIL]
    if person_email:
        host_recipients.append(person_email)
    
    host_body = (
        "<div style='font-family:Arial;padding:20px;background:#E8F5E9;border-radius:10px'>"
        "<h2 style='color:#2E7D32'>&#10003; Guest Approved!</h2>"
        "<p><b>Guest:</b> " + str(v["name"]) + "</p>"
        "<p><b>Purpose:</b> " + str(v["purpose"]) + "</p>"
        "<p><b>Time:</b> " + now + "</p>"
        "</div>"
    )
    threading.Thread(target=send_email, args=(host_recipients, "Guest Approved: " + str(v["name"]), host_body), daemon=True).start()
    
    # Pantry + Admin - Water serve karo
    pantry_body = (
        "<div style='font-family:Arial;padding:20px;background:#E3F2FD;border-radius:10px'>"
        "<h2 style='color:#1565C0'>&#128100; New Guest Arrived!</h2>"
        "<p><b>Guest:</b> " + str(v["name"]) + "</p>"
        "<p><b>Meeting:</b> " + str(v["person_to_meet"]) + "</p>"
        "<p><b>Time:</b> " + now + "</p>"
        "<p style='color:#F57F17;font-weight:bold;margin-top:10px'>&#128167; Please serve Water immediately.</p>"
        "</div>"
    )
    threading.Thread(target=send_email, args=([PANTRY_EMAIL, ADMIN_EMAIL], "Guest Arrived - Serve Water: " + str(v["name"]), pantry_body), daemon=True).start()
    
    # 5 min baad - Host ne reminder
    def five_min_reminder():
        import time
        time.sleep(300)
        person_email2 = EMPLOYEE_EMAILS.get(v["person_to_meet"])
        if person_email2:
            reminder_body = (
                "<div style='font-family:Arial;padding:20px;background:#FFF8E1;border-radius:10px'>"
                "<h3>&#9749; Tea/Coffee Time?</h3>"
                "<p>Guest <b>" + str(v["name"]) + "</b> has been here 5 minutes.</p>"
                "<p>Please select a beverage from your dashboard:</p>"
                "<a href='https://maxwell-visitor-app-2.onrender.com/employee-dashboard' "
                "style='background:#1565C0;color:white;padding:10px 20px;border-radius:5px;text-decoration:none'>Order Beverage</a>"
                "</div>"
            )
            send_email([person_email2, ADMIN_EMAIL], "5 Min Reminder - " + str(v["name"]), reminder_body)
    
    threading.Thread(target=five_min_reminder, daemon=True).start()

def notify_beverage_order(data, now):
    """Beverage order - Pantry + Admin + Host ne notification"""
    person_email = EMPLOYEE_EMAILS.get(data.get("person_to_meet",""))
    recipients = [PANTRY_EMAIL, ADMIN_EMAIL]
    if person_email and person_email not in recipients:
        recipients.append(person_email)
    
    body = (
        "<div style='font-family:Arial;padding:20px;background:#E3F2FD;border-radius:10px'>"
        "<h3>&#9749; New Beverage Order</h3>"
        "<p><b>Guest:</b> " + str(data.get("visitor_name","")) + "</p>"
        "<p><b>Host:</b> " + str(data.get("person_to_meet","")) + "</p>"
        "<p><b>Drink:</b> " + str(data.get("drink","")) + " x" + str(data.get("quantity",1)) + "</p>"
        + ("<p><b>Snacks:</b> " + str(data.get("snacks","")) + "</p>" if data.get("snacks") else "") +
        ("<p><b>Note:</b> " + str(data.get("note","")) + "</p>" if data.get("note") else "") +
        "<p><b>Time:</b> " + now + "</p>"
        "<a href='https://maxwell-visitor-app-2.onrender.com/pantry' style='background:#1565C0;color:white;padding:10px 20px;border-radius:5px;text-decoration:none;display:inline-block;margin-top:10px'>View Pantry Dashboard</a>"
        "</div>"
    )
    threading.Thread(target=send_email, args=(recipients, "Beverage Order: " + str(data.get("visitor_name","")), body), daemon=True).start()

# ── QR ────────────────────────────────────────────────────
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

# ── SCHEDULER ─────────────────────────────────────────────
def send_daily_summary():
    try:
        today = datetime.now().strftime("%d-%m-%Y")
        conn = get_db()
        visitors = [dict(r) for r in conn.execute(
            "SELECT * FROM visitors WHERE created_at LIKE ?", (today + "%",)
        ).fetchall()]
        conn.close()
        if not visitors:
            return
        rows = ""
        for v in visitors:
            co = v["checkout_at"] or "-"
            rows += "<tr><td>" + str(v["name"]) + "</td><td>" + str(v["phone"]) + "</td><td>" + str(v["department"]) + "</td><td>" + str(v["person_to_meet"]) + "</td><td>" + str(v["status"]) + "</td><td>" + str(v["created_at"]) + "</td><td>" + co + "</td></tr>"
        body = (
            "<div style='font-family:Arial;max-width:750px;margin:auto'>"
            "<div style='background:#1565C0;color:white;padding:20px;text-align:center'>"
            "<h2>Maxwell Engineering Solutions</h2><p>Daily Visitor Summary — " + today + "</p></div>"
            "<div style='padding:20px'><p>Total Visitors: <b>" + str(len(visitors)) + "</b></p>"
            "<table style='width:100%;border-collapse:collapse;margin-top:15px'>"
            "<tr style='background:#1565C0;color:white'><th style='padding:8px'>Name</th><th>Phone</th><th>Dept</th><th>Meeting</th><th>Status</th><th>In</th><th>Out</th></tr>"
            + rows + "</table></div></div>"
        )
        send_email([ADMIN_EMAIL, HOST_NOTIFY_EMAIL], "Daily Summary — " + today, body)
    except Exception as e:
        print("Daily summary error:", e)

if HAS_SCHEDULER:
    try:
        scheduler = BackgroundScheduler()
        scheduler.add_job(send_daily_summary, 'cron', hour=18, minute=0)
        scheduler.start()
    except:
        pass

# ═══════════════════════════════════════════════════════════
# VISITOR FORM
# ═══════════════════════════════════════════════════════════
@app.route("/")
def index():
    return build_visitor_form({})

def build_visitor_form(prefill):
    pname  = prefill.get("name","")
    pphone = prefill.get("phone","")
    ppurp  = prefill.get("purpose","")
    depts_js   = str(DEPARTMENTS).replace("'", '"')
    factory_js = str(FACTORY_DEPTS).replace("'", '"')
    mgmt_js    = str(MANAGEMENT_LIST).replace("'", '"')

    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Maxwell - Visitor Management</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Arial,sans-serif;background:#f0f4f8}
.header{background:white;padding:12px 20px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 8px rgba(0,0,0,0.1);border-bottom:3px solid #1565C0}
.hdr-title h1{color:#1565C0;font-size:16px;font-weight:900;text-align:center}
.hdr-title p{color:#777;font-size:10px;text-align:center}
.nav a{color:#1565C0;text-decoration:none;font-size:12px;padding:6px 12px;border:1.5px solid #1565C0;border-radius:6px;margin-left:5px;font-weight:600}
.nav a:hover{background:#1565C0;color:white}
.container{max-width:640px;margin:20px auto;padding:0 12px}
.card{background:white;border-radius:12px;padding:18px 20px;box-shadow:0 3px 10px rgba(0,0,0,0.07);margin-bottom:14px}
.section-title{font-size:14px;font-weight:700;color:#333;margin-bottom:14px}
.field-label{font-size:13px;font-weight:600;color:#555;margin-bottom:5px;display:block}
.req{color:#e53935}
input[type=text],input[type=tel],textarea{width:100%;padding:10px 12px;border:1.5px solid #ddd;border-radius:8px;font-size:14px;background:#fafafa;font-family:inherit;outline:none}
input:focus,textarea:focus{border-color:#1565C0;background:white}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}
.row1{margin-bottom:12px}
.cat-chip input[type=radio]{display:none}
.cat-chip label{display:inline-block;padding:8px 18px;border-radius:25px;border:2px solid #ddd;font-size:13px;font-weight:600;cursor:pointer;color:#555;background:white;transition:0.2s}
.cat-chip input:checked+label{background:#1565C0;color:white;border-color:#1565C0}
.chip{padding:8px 15px;border-radius:20px;border:1.5px solid #ddd;font-size:13px;font-weight:600;cursor:pointer;color:#555;background:white;transition:0.2s}
.chip:hover,.chip.selected{background:#1565C0;color:white;border-color:#1565C0}
.hidden{display:none}
.camera-area{text-align:center;padding:8px 0}
#video{width:100%;max-width:340px;border-radius:8px;border:2px solid #ddd;display:none}
#photo-preview{width:100px;height:100px;border-radius:50%;object-fit:cover;border:3px solid #1565C0;display:none;margin:8px auto}
#ph-icon{font-size:55px;color:#ddd;margin:6px 0;display:block}
.btn{padding:8px 16px;border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;margin:3px}
.btn-blue{background:#1565C0;color:white}
.btn-green{background:#2E7D32;color:white}
.btn-red{background:#C62828;color:white}
.submit-btn{width:100%;padding:14px;font-size:15px;border-radius:10px;background:linear-gradient(135deg,#1565C0,#1976D2);color:white;border:none;cursor:pointer;font-weight:700;letter-spacing:1px}
.alert{padding:11px 16px;border-radius:8px;margin-bottom:12px;font-size:14px;font-weight:500}
.alert-error{background:#ffebee;color:#C62828;border:1px solid #ef9a9a}
.submitted-msg{text-align:center;padding:25px}
.history-item{background:#f5f5f5;border-radius:8px;padding:10px;margin-bottom:8px;cursor:pointer;border:1.5px solid #ddd}
.history-item:hover{border-color:#1565C0;background:#e3f2fd}
@media(max-width:540px){.row2{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="header">
  <div>
    <div class="hdr-title"><h1>Maxwell Visitor Management</h1><p>Maxwell Engineering Solutions</p></div>
  </div>
  <div class="nav"><a href="/admin">Admin</a><a href="/employee-login">Employee</a><a href="/pantry-login">Pantry</a></div>
</div>
<div class="container">
  <div id="alert-box"></div>
  <div id="history-section" class="card hidden">
    <div class="section-title">Previous Visits Found</div>
    <div id="history-list"></div>
    <button class="btn btn-blue" onclick="clearHistory()" style="margin-top:8px">+ New Entry</button>
  </div>
  <div id="form-section">
    <div class="card">
      <div class="section-title">Visitor Entry</div>
      <div class="row2">
        <div><label class="field-label">Full Name <span class="req">*</span></label>
        <input type="text" id="v-name" placeholder="Enter full name" value="PNAME"></div>
        <div><label class="field-label">Phone Number <span class="req">*</span></label>
        <input type="tel" id="v-phone" placeholder="Mobile number" value="PPHONE" oninput="searchHistory()"></div>
      </div>
      <div class="row1"><label class="field-label">Name of Host</label>
      <input type="text" id="v-host" placeholder="Who are you visiting?"></div>
      <div class="row1"><label class="field-label">Purpose of Visit <span class="req">*</span></label>
      <textarea id="v-purpose" rows="2" placeholder="Brief purpose">PPURP</textarea></div>
    </div>
    <div class="card">
      <div class="section-title">Visitor Category <span class="req">*</span></div>
      <div style="display:flex;flex-wrap:wrap;gap:8px">
        <div class="cat-chip"><input type="radio" name="category" id="cat-f" value="Factory Visit" onchange="onCat()"><label for="cat-f">Factory Visit</label></div>
        <div class="cat-chip"><input type="radio" name="category" id="cat-s" value="Staff Visit" onchange="onCat()"><label for="cat-s">Staff Visit</label></div>
        <div class="cat-chip"><input type="radio" name="category" id="cat-m" value="Management" onchange="onCat()"><label for="cat-m">Management</label></div>
      </div>
    </div>
    <div class="card hidden" id="dept-card">
      <div class="section-title">Department <span class="req">*</span></div>
      <div style="display:flex;flex-wrap:wrap;gap:8px" id="dept-group"></div>
    </div>
    <div class="card hidden" id="person-card">
      <div class="section-title">Person to Meet <span class="req">*</span></div>
      <div style="display:flex;flex-wrap:wrap;gap:8px" id="person-group"></div>
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
      <h2 style="color:#2E7D32">Request Submitted!</h2>
      <p style="color:#666;margin-top:8px">Awaiting approval. Pass ready once approved.</p>
      <br><button class="btn btn-blue" onclick="location.reload()">+ New Visitor</button>
    </div>
  </div>
</div>
<script>
var DEPTS=DEPTS_JS;
var FACTORY=FACTORY_JS;
var MGMT=MGMT_JS;
var photoData=null,camStream=null,selDept="",selPerson="";

function searchHistory(){
  var phone=document.getElementById('v-phone').value.trim();
  if(phone.length<10)return;
  fetch('/api/history?phone='+phone).then(r=>r.json()).then(d=>{
    if(d.visitors&&d.visitors.length>0){
      var html='';
      d.visitors.forEach(function(v){
        html+='<div class="history-item" onclick="fillHistory('+JSON.stringify(v)+')">';
        html+='<strong>'+v.name+'</strong> — '+v.purpose+'<br>';
        html+='<small style="color:#888">Last visit: '+v.created_at+'</small></div>';
      });
      document.getElementById('history-list').innerHTML=html;
      document.getElementById('history-section').classList.remove('hidden');
    }
  }).catch(()=>{});
}
function fillHistory(v){
  document.getElementById('v-name').value=v.name||'';
  document.getElementById('v-host').value=v.host_name||'';
  document.getElementById('v-purpose').value=v.purpose||'';
  document.getElementById('history-section').classList.add('hidden');
}
function clearHistory(){document.getElementById('history-section').classList.add('hidden');}

function onCat(){
  var cat=document.querySelector('input[name="category"]:checked');
  if(!cat)return;
  var val=cat.value;
  selDept='';selPerson='';
  document.getElementById('dept-card').classList.add('hidden');
  document.getElementById('person-card').classList.add('hidden');
  document.getElementById('dept-group').innerHTML='';
  document.getElementById('person-group').innerHTML='';
  if(val==='Factory Visit'){
    document.getElementById('dept-card').classList.remove('hidden');
    Object.keys(FACTORY).forEach(function(d){addChip('dept-group',d,function(){selectDept(d,val);});});
  }else if(val==='Staff Visit'){
    document.getElementById('dept-card').classList.remove('hidden');
    Object.keys(DEPTS).forEach(function(d){addChip('dept-group',d,function(){selectDept(d,val);});});
  }else if(val==='Management'){
    document.getElementById('person-card').classList.remove('hidden');
    showPersons(MGMT);
  }
}
function addChip(groupId,label,onclick){
  var el=document.createElement('div');
  el.className='chip';el.textContent=label;
  el.onclick=function(){el.onclick=onclick;onclick();};
  document.getElementById(groupId).appendChild(el);
}
function selectDept(dept,cat){
  selDept=dept;selPerson='';
  document.querySelectorAll('#dept-group .chip').forEach(function(c){c.classList.remove('selected');});
  event.target.classList.add('selected');
  document.getElementById('person-group').innerHTML='';
  document.getElementById('others-input').classList.add('hidden');
  if(dept==='Others'){
    document.getElementById('person-card').classList.remove('hidden');
    document.getElementById('others-input').classList.remove('hidden');
    return;
  }
  document.getElementById('person-card').classList.remove('hidden');
  var list=(cat==='Factory Visit')?FACTORY[dept]:DEPTS[dept];
  if(list)showPersons(list);
}
function showPersons(list){
  var pg=document.getElementById('person-group');pg.innerHTML='';
  list.forEach(function(p){
    var c=document.createElement('div');c.className='chip';c.textContent=p;
    c.onclick=function(){
      selPerson=p;
      document.querySelectorAll('#person-group .chip').forEach(function(x){x.classList.remove('selected');});
      c.classList.add('selected');
    };
    pg.appendChild(c);
  });
}
async function startCam(){
  try{
    camStream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'user'}});
    document.getElementById('video').srcObject=camStream;
    document.getElementById('video').style.display='block';
    document.getElementById('ph-icon').style.display='none';
    document.getElementById('photo-preview').style.display='none';
    document.getElementById('cap-btn').style.display='';
    document.getElementById('ret-btn').style.display='none';
  }catch(e){alert('Camera access denied!');}
}
function capPhoto(){
  var v=document.getElementById('video'),c=document.getElementById('canvas');
  c.width=v.videoWidth||320;c.height=v.videoHeight||320;
  c.getContext('2d').drawImage(v,0,0);
  photoData=c.toDataURL('image/jpeg',0.8);
  document.getElementById('photo-preview').src=photoData;
  document.getElementById('photo-preview').style.display='block';
  document.getElementById('video').style.display='none';
  document.getElementById('cap-btn').style.display='none';
  document.getElementById('ret-btn').style.display='';
  if(camStream)camStream.getTracks().forEach(function(t){t.stop();});
}
function retake(){
  photoData=null;
  document.getElementById('photo-preview').style.display='none';
  document.getElementById('ret-btn').style.display='none';
  document.getElementById('ph-icon').style.display='block';
  startCam();
}
function showAlert(msg){
  document.getElementById('alert-box').innerHTML='<div class="alert alert-error">'+msg+'</div>';
  setTimeout(function(){document.getElementById('alert-box').innerHTML='';},5000);
}
async function submitForm(){
  var name=document.getElementById('v-name').value.trim();
  var phone=document.getElementById('v-phone').value.trim();
  var purpose=document.getElementById('v-purpose').value.trim();
  var host=document.getElementById('v-host').value.trim();
  var catEl=document.querySelector('input[name="category"]:checked');
  var cat=catEl?catEl.value:'';
  var dept=selDept||'Management';
  var person=selPerson;
  if(dept==='Others')person=document.getElementById('v-others').value.trim();
  if(!name){showAlert('Please enter visitor name!');return;}
  if(!phone){showAlert('Please enter phone number!');return;}
  if(!purpose){showAlert('Please enter purpose!');return;}
  if(!cat){showAlert('Please select visitor category!');return;}
  if(!person){showAlert('Please select person to meet!');return;}
  try{
    var res=await fetch('/api/visitor',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name:name,phone:phone,purpose:purpose,host_name:host,category:cat,department:dept,person_to_meet:person,photo:photoData})});
    var data=await res.json();
    if(data.success){
      document.getElementById('form-section').classList.add('hidden');
      document.getElementById('submitted-section').classList.remove('hidden');
    }else{showAlert('Error: '+(data.error||'Unknown error'));}
  }catch(e){showAlert('Server error!');}
}
</script>
</body>
</html>""".replace("DEPTS_JS", depts_js).replace("FACTORY_JS", factory_js).replace("MGMT_JS", mgmt_js).replace("PNAME", pname).replace("PPHONE", pphone).replace("PPURP", ppurp)

@app.route("/api/history")
def visitor_history():
    phone = request.args.get("phone","")
    conn = get_db()
    visitors = [dict(r) for r in conn.execute(
        "SELECT name,phone,purpose,host_name,created_at FROM visitors WHERE phone=? ORDER BY id DESC LIMIT 3",(phone,)
    ).fetchall()]
    conn.close()
    return jsonify({"visitors": visitors})

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
        (data.get("name"),data.get("phone"),data.get("purpose"),data.get("host_name"),
         data.get("category"),data.get("department"),data.get("person_to_meet"),
         data.get("photo"),now,pass_num)
    )
    vid = c.lastrowid
    conn.commit()
    v = dict(conn.execute("SELECT * FROM visitors WHERE id=?",(vid,)).fetchone())
    conn.close()
    notify_new_visitor(v)
    return jsonify({"success": True, "id": vid})

@app.route("/api/pending-count")
def pending_count():
    conn = get_db()
    row = conn.execute("SELECT COUNT(*) as cnt FROM visitors WHERE status='pending'").fetchone()
    conn.close()
    return jsonify({"count": row["cnt"]})

@app.route("/action/<int:vid>/<action>")
def do_action(vid, action):
    if action not in ("approve","reject"):
        return "Invalid", 400
    conn = get_db()
    conn.execute("UPDATE visitors SET status=? WHERE id=?", (action+"d", vid))
    conn.commit()
    if action == "approve":
        v = dict(conn.execute("SELECT * FROM visitors WHERE id=?",(vid,)).fetchone())
        conn.close()
        now = datetime.now().strftime("%d-%m-%Y %H:%M")
        conn2 = get_db()
        conn2.execute(
            "INSERT INTO pantry_orders (visitor_id,visitor_name,person_to_meet,drink,quantity,note,created_at,order_type) VALUES (?,?,?,?,?,?,?,?)",
            (vid, v["name"], v["person_to_meet"], "Water", 1, "Guest arrived", now, "arrival")
        )
        conn2.commit()
        conn2.close()
        notify_approved(v, now)
    else:
        conn.close()
    if "application/json" in request.headers.get("Accept",""):
        return jsonify({"success": True})
    return (
        "<h2 style='text-align:center;margin-top:80px;font-family:Arial;color:#1565C0'>"
        "Visitor " + action.title() + "d!<br><br>"
        "<a href='/admin'>Admin Panel</a> &nbsp;|&nbsp; "
        "<a href='/pass/" + str(vid) + "'>View Pass</a></h2>"
    )

@app.route("/api/checkout/<int:vid>", methods=["POST"])
def checkout_visitor(vid):
    now = datetime.now().strftime("%d-%m-%Y %H:%M")
    conn = get_db()
    conn.execute("UPDATE visitors SET checkout_at=? WHERE id=?",(now,vid))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "checkout_at": now})

@app.route("/api/beverage", methods=["POST"])
def order_beverage():
    data = request.get_json()
    now = datetime.now().strftime("%d-%m-%Y %H:%M")
    conn = get_db()
    conn.execute(
        "INSERT INTO pantry_orders (visitor_id,visitor_name,person_to_meet,drink,snacks,quantity,note,created_at,order_type) VALUES (?,?,?,?,?,?,?,?,?)",
        (data.get("visitor_id"),data.get("visitor_name"),data.get("person_to_meet"),
         data.get("drink",""),data.get("snacks",""),data.get("quantity",1),
         data.get("note",""),now,"order")
    )
    conn.commit()
    conn.close()
    notify_beverage_order(data, now)
    return jsonify({"success": True})

@app.route("/pass/<int:vid>")
def show_pass(vid):
    conn = get_db()
    row = conn.execute("SELECT * FROM visitors WHERE id=?",(vid,)).fetchone()
    conn.close()
    if not row:
        return "Not found", 404
    v = dict(row)
    if v["status"] != "approved":
        return "<h2 style='text-align:center;margin-top:80px;font-family:Arial;color:#C62828'>Pass not available. Must be approved first.<br><br><a href='/admin' style='color:#1565C0'>Admin Panel</a></h2>"
    bg, fg, label = PASS_COLORS.get(v["category"], ("1565C0","FFFFFF","VISITOR"))
    photo = v.get("photo") or DEFAULT_PHOTO
    qr = make_qr("Maxwell\nName: " + v["name"] + "\nPass: " + v["pass_number"] + "\nTime: " + v["created_at"])
    qr_img = '<img src="data:image/png;base64,' + qr + '" width="90">' if qr else ""
    return (
        "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Visitor Pass</title>"
        "<style>*{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important}"
        "body{font-family:Arial;background:#f0f0f0;display:flex;justify-content:center;padding:30px;flex-direction:column;align-items:center}"
        ".pass{width:370px;border-radius:14px;overflow:hidden;box-shadow:0 8px 25px rgba(0,0,0,0.2)}"
        ".ph{padding:15px 20px;display:flex;justify-content:space-between;align-items:center;background:#" + bg + ";color:#" + fg + "}"
        ".pb{background:white;padding:20px}.pf{background:#f5f5f5;text-align:center;padding:10px;font-size:11px;color:#888}"
        ".pp{width:78px;height:78px;border-radius:50%;object-fit:cover;border:3px solid white}"
        ".il{font-size:11px;color:#888;text-transform:uppercase;margin-bottom:2px}.iv{font-size:14px;font-weight:600;color:#222;margin-bottom:10px}"
        ".appr{background:#E8F5E9;color:#2E7D32;text-align:center;padding:8px;border-radius:5px;font-weight:700;margin-top:10px}"
        ".btns{margin-top:20px;text-align:center}"
        "@media print{body{background:white;padding:0}.btns{display:none}}</style></head><body>"
        "<div class='pass'>"
        "<div class='ph'><div style='font-size:18px;font-weight:900'>Maxwell</div>"
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
        "<div class='il'>Date & Time</div><div class='iv'>" + str(v["created_at"]) + "</div>"
        "<div style='text-align:center;margin-top:12px'>" + qr_img + "</div>"
        "<div class='appr'>&#10003; APPROVED</div></div>"
        "<div class='pf'>Maxwell Engineering Solutions | Visitor Management System</div></div>"
        "<div class='btns'>"
        "<button onclick='window.print()' style='background:#1565C0;color:white;padding:10px 20px;border:none;border-radius:7px;cursor:pointer;font-size:14px'>Print Pass</button>"
        "<button onclick='window.close()' style='background:#666;color:white;padding:10px 20px;border:none;border-radius:7px;cursor:pointer;font-size:14px;margin-left:10px'>Close</button>"
        "</div><script>setTimeout(function(){window.print();},600);</script>"
        "</body></html>"
    )

# ── ADMIN ─────────────────────────────────────────────────
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
        "<input type='password' name='pin' placeholder='Enter Admin PIN'>"
        "<button type='submit'>LOGIN</button></form>"
        + ("<p class='err'>" + err + "</p>" if err else "") +
        "<a href='/'>Back to Visitor Form</a></div></body></html>"
    )

@app.route("/admin")
def admin():
    if not session.get("admin_ok"):
        return admin_login_page("")
    session.modified = True
    tab = request.args.get("tab","pending")
    conn = get_db()
    if tab == "all":
        visitors = [dict(r) for r in conn.execute("SELECT * FROM visitors WHERE status != 'advance' ORDER BY id DESC").fetchall()]
    else:
        visitors = [dict(r) for r in conn.execute("SELECT * FROM visitors WHERE status=? ORDER BY id DESC",(tab,)).fetchall()]
    counts = {}
    for r in conn.execute("SELECT status,COUNT(*) as cnt FROM visitors GROUP BY status").fetchall():
        counts[r["status"]] = r["cnt"]
    conn.close()
    pc = counts.get("pending",0); ac = counts.get("approved",0); rc = counts.get("rejected",0)

    rows = ""
    for v in visitors:
        bc = "pending" if v["status"]=="pending" else ("approved" if v["status"]=="approved" else "rejected")
        photo = v["photo"] if v["photo"] else DEFAULT_PHOTO
        ab = ""
        if v["status"] == "pending":
            ab += '<button class="btn ba" onclick="act('+str(v["id"])+',' + "'approve'" + ')">&#10003; Approve</button>'
            ab += '<button class="btn br" onclick="act('+str(v["id"])+',' + "'reject'" + ')">&#10005; Reject</button>'
        if v["status"] == "approved" and not v.get("checkout_at"):
            ab += '<button class="btn bc" onclick="checkout('+str(v["id"])+')">&#128682; Checkout</button>'
        ab += '<button class="btn bp" onclick="window.open(\'/pass/'+str(v["id"])+'\')">Pass</button>'
        co = v.get("checkout_at") or "-"
        rows += (
            "<tr><td><img src='" + photo + "' style='width:42px;height:42px;border-radius:50%;object-fit:cover;border:2px solid #ddd'></td>"
            "<td><strong>" + str(v["name"]) + "</strong></td>"
            "<td>" + str(v["phone"]) + "</td>"
            "<td>" + str(v["category"]) + "</td>"
            "<td>" + str(v["department"]) + "</td>"
            "<td>" + str(v["person_to_meet"]) + "</td>"
            "<td style='font-size:11px'>" + str(v["created_at"]) + "</td>"
            "<td style='font-size:11px'>" + co + "</td>"
            "<td><span class='badge " + bc + "'>" + v["status"].upper() + "</span></td>"
            "<td>" + ab + "</td></tr>"
        )
    if not rows:
        rows = '<tr><td colspan="10" style="text-align:center;padding:25px;color:#999">No records</td></tr>'

    tab_a = {"pending":"","approved":"","rejected":"","all":""}
    tab_a[tab] = "active"

    return (
        "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Maxwell Admin</title>"
        "<style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:Arial;background:#f0f4f8}"
        ".header{background:#1565C0;color:white;padding:13px 25px;display:flex;justify-content:space-between;align-items:center}"
        ".header h1{font-size:18px}"
        ".header a{color:white;text-decoration:none;background:rgba(255,255,255,0.2);padding:7px 13px;border-radius:5px;font-size:13px;margin-left:7px}"
        ".container{max-width:1200px;margin:20px auto;padding:0 15px}"
        ".stats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:20px}"
        ".stat{background:white;border-radius:9px;padding:18px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.07)}"
        ".stat-n{font-size:34px;font-weight:900}.stat-l{font-size:12px;color:#666;margin-top:4px}"
        ".pend{color:#F57F17}.appr{color:#2E7D32}.reje{color:#C62828}"
        ".tabs{display:flex;gap:4px;margin-bottom:15px}"
        ".tab{padding:9px 18px;border:none;border-radius:7px 7px 0 0;cursor:pointer;font-weight:600;font-size:13px;background:#ddd;color:#555}"
        ".tab.active{background:white;color:#1565C0}"
        ".card{background:white;border-radius:9px;padding:18px;box-shadow:0 2px 8px rgba(0,0,0,0.07);overflow-x:auto}"
        "table{width:100%;border-collapse:collapse;min-width:950px}"
        "th{background:#1565C0;color:white;padding:11px;text-align:left;font-size:12px}"
        "td{padding:9px;border-bottom:1px solid #eee;font-size:13px;vertical-align:middle}"
        "tr:hover td{background:#f9f9f9}"
        ".badge{display:inline-block;padding:3px 9px;border-radius:11px;font-size:11px;font-weight:700}"
        ".badge.pending{background:#FFF8E1;color:#F57F17}"
        ".badge.approved{background:#E8F5E9;color:#2E7D32}"
        ".badge.rejected{background:#FFEBEE;color:#C62828}"
        ".btn{padding:5px 10px;border:none;border-radius:5px;cursor:pointer;font-size:11px;font-weight:600;margin:2px}"
        ".ba{background:#2E7D32;color:white}.br{background:#C62828;color:white}"
        ".bp{background:#1565C0;color:white}.bc{background:#FF6F00;color:white}"
        "</style></head><body>"
        "<div class='header'><h1>Maxwell Admin Panel</h1>"
        "<div><a href='/pantry'>&#9749; Pantry</a><a href='/'>Visitor Form</a><a href='/admin-logout'>Logout</a></div></div>"
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
        "<tr><th>Photo</th><th>Name</th><th>Phone</th><th>Category</th><th>Dept</th><th>Meeting</th><th>In Time</th><th>Out Time</th><th>Status</th><th>Action</th></tr>"
        + rows +
        "</table></div></div>"
        "<script>"
        "var _lc=0;"
        "async function act(id,action){"
        "if(!confirm(action+' this visitor?'))return;"
        "var r=await fetch('/action/'+id+'/'+action,{headers:{'Accept':'application/json'}});"
        "var d=await r.json();"
        "if(action==='approve'){window.open('/pass/'+id);}"
        "location.reload();}"
        "async function checkout(id){"
        "if(!confirm('Checkout this visitor?'))return;"
        "await fetch('/api/checkout/'+id,{method:'POST'});"
        "location.reload();}"
        "async function _chkNew(){"
        "try{var r=await fetch('/api/pending-count');var d=await r.json();"
        "if(_lc>0&&d.count>_lc){_beep();"
        "if(Notification.permission==='granted'){new Notification('Maxwell',{body:'New visitor request!',icon:'/favicon.ico'});}}"
        "_lc=d.count;document.title=d.count>0?'('+d.count+') New! - Maxwell Admin':'Maxwell Admin';"
        "}catch(e){}}"
        "function _beep(){"
        "try{var c=new(window.AudioContext||window.webkitAudioContext)();"
        "var notes=[880,660,880,1100];"
        "notes.forEach(function(freq,i){"
        "var o=c.createOscillator(),g=c.createGain();"
        "o.connect(g);g.connect(c.destination);"
        "o.frequency.value=freq;o.type='sine';"
        "var t=c.currentTime+i*0.2;"
        "g.gain.setValueAtTime(0,t);"
        "g.gain.linearRampToValueAtTime(1.5,t+0.05);"
        "g.gain.exponentialRampToValueAtTime(0.001,t+0.35);"
        "o.start(t);o.stop(t+0.35);});"
        "}catch(e){}}"
        "if(Notification.permission==='default'){Notification.requestPermission();}"
        "setInterval(_chkNew,8000);_chkNew();"
        "</script></body></html>"
    )

@app.route("/admin-login", methods=["POST"])
def admin_login():
    if request.form.get("pin","") == ADMIN_PIN:
        session["admin_ok"] = True
        return redirect("/admin")
    return admin_login_page("Wrong PIN! Try again.")

@app.route("/admin-logout")
def admin_logout():
    session.clear()
    return redirect("/admin")

# ── PANTRY ────────────────────────────────────────────────
@app.route("/pantry-login", methods=["GET","POST"])
def pantry_login():
    err = ""
    if request.method == "POST":
        email = request.form.get("email","").strip()
        pwd   = request.form.get("password","").strip()
        if email == PANTRY_EMAIL and pwd == PANTRY_PASSWORD:
            session["pantry_ok"] = True
            return redirect("/pantry")
        err = "Wrong credentials! Email: maxwellvisitor05@gmail.com / Password: MaxwellPantry2024"
    return (
        "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Pantry Login</title>"
        "<style>body{font-family:Arial;background:#f0f4f8}"
        ".header{background:#1565C0;color:white;padding:13px 25px}"
        ".box{max-width:400px;margin:70px auto;background:white;padding:38px;border-radius:13px;box-shadow:0 5px 18px rgba(0,0,0,0.1)}"
        ".box h2{color:#1565C0;text-align:center;margin-bottom:22px}"
        "label{display:block;font-size:13px;font-weight:600;color:#444;margin-bottom:5px;margin-top:14px}"
        "input{width:100%;padding:11px;border:2px solid #e0e0e0;border-radius:7px;font-size:14px}"
        "input:focus{outline:none;border-color:#1565C0}"
        "button{width:100%;margin-top:18px;padding:12px;background:#1565C0;color:white;border:none;border-radius:7px;font-size:15px;font-weight:700;cursor:pointer}"
        ".err{color:red;font-size:13px;margin-top:8px;text-align:center}"
        ".hint{background:#e3f2fd;padding:10px;border-radius:6px;font-size:12px;color:#1565C0;margin-top:10px}"
        "</style></head><body>"
        "<div class='header'><h1>Maxwell Engineering Solutions — Pantry</h1></div>"
        "<div class='box'><h2>&#9749; Pantry Login</h2>"
        "<form method='POST'>"
        "<label>Email</label><input type='email' name='email' value='maxwellvisitor05@gmail.com'>"
        "<label>Password</label><input type='password' name='password' placeholder='MaxwellPantry2024'>"
        "<button type='submit'>LOGIN</button></form>"
        + ("<p class='err'>" + err + "</p>" if err else "") +
        "<div class='hint'>Email: maxwellvisitor05@gmail.com<br>Password: MaxwellPantry2024</div>"
        "</div></body></html>"
    )

@app.route("/pantry")
def pantry():
    if not session.get("pantry_ok") and not session.get("admin_ok"):
        return redirect("/pantry-login")
    conn = get_db()
    orders = [dict(r) for r in conn.execute(
        "SELECT * FROM pantry_orders ORDER BY id DESC LIMIT 60"
    ).fetchall()]
    conn.close()

    rows = ""
    for o in orders:
        status_badge = "pending" if o["status"]=="pending" else "delivered"
        timer_html = ""
        if o["status"] == "pending" and o.get("timer_start"):
            timer_html = '<div id="tmr-'+str(o["id"])+'" style="color:#F57F17;font-size:11px;font-weight:600"></div>'
        ab = ""
        if o["status"] == "pending":
            ab = '<button class="btn ba" onclick="deliverOrder('+str(o["id"])+',' + "'drink'" + ')">&#10003; Delivered</button>'
        
        drink_info = str(o["drink"]) if o.get("drink") else "-"
        snacks_info = str(o["snacks"]) if o.get("snacks") else "-"
        
        rows += (
            "<tr id='row-"+str(o["id"])+"'>"
            "<td><strong>" + str(o["visitor_name"]) + "</strong></td>"
            "<td>" + str(o["person_to_meet"]) + "</td>"
            "<td>" + drink_info + " x" + str(o["quantity"]) + "</td>"
            "<td>" + snacks_info + "</td>"
            "<td>" + str(o["note"] or "-") + "</td>"
            "<td style='font-size:11px'>" + str(o["created_at"]) + "</td>"
            "<td><span class='badge " + status_badge + "'>" + o["status"].upper() + "</span>" + timer_html + "</td>"
            "<td>" + ab + "</td></tr>"
        )
    if not rows:
        rows = '<tr><td colspan="8" style="text-align:center;padding:25px;color:#999">No orders</td></tr>'

    return (
        "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Pantry Dashboard</title>"
        "<style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:Arial;background:#f0f4f8}"
        ".header{background:#1565C0;color:white;padding:13px 25px;display:flex;justify-content:space-between;align-items:center}"
        ".header a{color:white;text-decoration:none;background:rgba(255,255,255,0.2);padding:7px 13px;border-radius:5px;font-size:13px;margin-left:7px}"
        ".container{max-width:1000px;margin:20px auto;padding:0 15px}"
        ".card{background:white;border-radius:9px;padding:18px;box-shadow:0 2px 8px rgba(0,0,0,0.07);overflow-x:auto;margin-bottom:15px}"
        ".card h3{color:#1565C0;margin-bottom:14px}"
        ".pending-banner{background:#FFF8E1;border:2px solid #F57F17;border-radius:9px;padding:15px;margin-bottom:15px;text-align:center;font-weight:700;color:#E65100;font-size:16px;display:none}"
        "table{width:100%;border-collapse:collapse;min-width:700px}"
        "th{background:#1565C0;color:white;padding:10px;font-size:12px;text-align:left}"
        "td{padding:10px;border-bottom:1px solid #eee;font-size:13px;vertical-align:middle}"
        "tr.pending-row{background:#FFF8E1}"
        ".badge{display:inline-block;padding:3px 9px;border-radius:11px;font-size:11px;font-weight:700}"
        ".badge.pending{background:#FFF8E1;color:#F57F17}"
        ".badge.delivered{background:#E8F5E9;color:#2E7D32}"
        ".btn{padding:6px 12px;border:none;border-radius:5px;cursor:pointer;font-size:12px;font-weight:600;margin:2px}"
        ".ba{background:#2E7D32;color:white}"
        "</style></head><body>"
        "<div class='header'><h1>&#9749; Pantry Dashboard</h1>"
        "<div><a href='/admin'>Admin</a><a href='/pantry-logout'>Logout</a></div></div>"
        "<div class='container'>"
        "<div class='pending-banner' id='pending-banner'>&#128276; NEW ORDER! Please check below!</div>"
        "<div class='card'>"
        "<h3>Beverage & Snack Orders</h3>"
        "<table><tr><th>Guest</th><th>Host</th><th>Drink & Qty</th><th>Snacks</th><th>Note</th><th>Time</th><th>Status</th><th>Action</th></tr>"
        + rows +
        "</table></div></div>"
        "<script>"
        "var _pc=0,_timers={};"
        "async function deliverOrder(id,type){"
        "var r=await fetch('/api/pantry-deliver/'+id,{method:'POST'});"
        "var d=await r.json();"
        "if(d.success){location.reload();}}"
        "async function checkOrders(){try{"
        "var r=await fetch('/api/pantry-pending');"
        "var d=await r.json();"
        "if(_pc>0&&d.count>_pc){"
        "_beep();"
        "document.getElementById('pending-banner').style.display='block';"
        "if(Notification.permission==='granted'){new Notification('Pantry - New Order!',{body:'New beverage order received!'});}"
        "setTimeout(function(){document.getElementById('pending-banner').style.display='none';},10000);}"
        "_pc=d.count;"
        "document.title=d.count>0?'('+d.count+') NEW ORDER! - Pantry':'Pantry Dashboard';"
        "}catch(e){}}"
        "function _beep(){"
        "try{var c=new(window.AudioContext||window.webkitAudioContext)();"
        "for(var i=0;i<5;i++){(function(n){"
        "var o=c.createOscillator(),g=c.createGain();"
        "o.connect(g);g.connect(c.destination);"
        "o.frequency.value=n%2===0?880:660;o.type='sine';"
        "var t=c.currentTime+n*0.3;"
        "g.gain.setValueAtTime(0,t);"
        "g.gain.linearRampToValueAtTime(2.0,t+0.05);"
        "g.gain.exponentialRampToValueAtTime(0.001,t+0.4);"
        "o.start(t);o.stop(t+0.4);})(i);}"
        "}catch(e){}}"
        "if(Notification.permission==='default'){Notification.requestPermission();}"
        "setInterval(checkOrders,6000);checkOrders();"
        "</script></body></html>"
    )

@app.route("/api/pantry-deliver/<int:oid>", methods=["POST"])
def pantry_deliver(oid):
    now = datetime.now().strftime("%d-%m-%Y %H:%M")
    conn = get_db()
    conn.execute("UPDATE pantry_orders SET status='delivered',delivered_at=? WHERE id=?",(now,oid))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/pantry-pending")
def pantry_pending():
    conn = get_db()
    row = conn.execute("SELECT COUNT(*) as cnt FROM pantry_orders WHERE status='pending'").fetchone()
    conn.close()
    return jsonify({"count": row["cnt"]})

@app.route("/pantry-logout")
def pantry_logout():
    session.pop("pantry_ok", None)
    return redirect("/pantry-login")

# ── EMPLOYEE ──────────────────────────────────────────────
@app.route("/employee-login", methods=["GET","POST"])
def employee_login():
    err = ""
    if request.method == "POST":
        email    = request.form.get("email","").lower().strip()
        password = request.form.get("password","").strip()
        emp_map  = {v.lower(): k for k, v in EMPLOYEE_EMAILS.items()}
        if email in emp_map:
            emp_name = emp_map[email]
            if password == emp_name:
                session["emp_name"] = emp_name
                return redirect("/employee-dashboard")
            else:
                err = "Wrong password! Use your full name as password."
        else:
            err = "Email not found."
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
        ".hint{background:#e3f2fd;padding:10px;border-radius:6px;font-size:12px;color:#1565C0;margin-top:10px}"
        "</style></head><body>"
        "<div class='header'><h1>Maxwell Engineering Solutions</h1></div>"
        "<div class='box'><h2>Employee Login</h2>"
        "<form method='POST'>"
        "<label>Company Email</label><input type='email' name='email' placeholder='yourname@maxwells.in' required>"
        "<label>Password</label><input type='password' name='password' placeholder='Your full name' required>"
        "<button type='submit'>LOGIN</button></form>"
        + ("<p class='err'>" + err + "</p>" if err else "") +
        "<div class='hint'>Password = Your full name (e.g. Vrunda Thakkar)</div>"
        "<a href='/'>Back to Visitor Form</a></div></body></html>"
    )

@app.route("/employee-dashboard")
def employee_dashboard():
    if not session.get("emp_name"):
        return redirect("/employee-login")
    name = session["emp_name"]
    conn = get_db()
    visitors = [dict(r) for r in conn.execute(
        "SELECT * FROM visitors WHERE person_to_meet=? AND status='approved' AND checkout_at IS NULL ORDER BY id DESC",(name,)
    ).fetchall()]
    all_visitors = [dict(r) for r in conn.execute(
        "SELECT * FROM visitors WHERE person_to_meet=? ORDER BY id DESC LIMIT 20",(name,)
    ).fetchall()]
    conn.close()

    drinks_opts = ""
    for d in DRINKS_MENU:
        drinks_opts += '<option value="' + d + '">' + d + '</option>'

    active_rows = ""
    for v in visitors:
        vid = str(v["id"])
        active_rows += (
            "<div style='background:#E3F2FD;border-radius:10px;padding:16px;margin-bottom:14px'>"
            "<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:10px'>"
            "<div><strong style='font-size:16px'>" + str(v["name"]) + "</strong>"
            "<span style='color:#666;font-size:12px;margin-left:10px'>" + str(v["created_at"]) + "</span></div>"
            "<button style='background:#C62828;color:white;border:none;padding:6px 12px;border-radius:5px;cursor:pointer;font-weight:600' onclick='checkout(" + vid + ")'>Checkout</button></div>"
            "<div style='font-size:13px;color:#444;margin-bottom:12px'>Purpose: " + str(v["purpose"]) + "</div>"

            "<!-- DRINK ORDER -->"
            "<div style='background:white;border-radius:8px;padding:12px;margin-bottom:10px'>"
            "<div style='font-size:13px;font-weight:700;color:#1565C0;margin-bottom:8px'>&#9749; Order Drink</div>"
            "<div style='display:flex;align-items:center;gap:10px;flex-wrap:wrap'>"
            "<select id='drk-" + vid + "' style='padding:8px 12px;border:1.5px solid #ddd;border-radius:8px;font-size:13px;flex:1;min-width:140px'>"
            "<option value=''>-- Select Drink --</option>" + drinks_opts + "</select>"
            "<div style='display:flex;align-items:center;gap:6px'>"
            "<button onclick='changeQty(\"" + vid + "\",-1)' style='width:32px;height:32px;border-radius:50%;border:1.5px solid #1565C0;background:white;color:#1565C0;font-size:18px;cursor:pointer;font-weight:700'>−</button>"
            "<span id='qty-" + vid + "' style='font-size:16px;font-weight:700;min-width:30px;text-align:center'>1</span>"
            "<button onclick='changeQty(\"" + vid + "\",1)' style='width:32px;height:32px;border-radius:50%;border:1.5px solid #1565C0;background:white;color:#1565C0;font-size:18px;cursor:pointer;font-weight:700'>+</button>"
            "</div></div>"
            "<input type='text' id='note-" + vid + "' placeholder='Special note (less sugar, add ginger...)' style='width:100%;padding:8px;border:1.5px solid #ddd;border-radius:6px;margin-top:8px;font-size:13px'>"
            "</div>"

            "<!-- SNACKS ORDER -->"
            "<div style='background:white;border-radius:8px;padding:12px;margin-bottom:10px'>"
            "<div style='font-size:13px;font-weight:700;color:#1565C0;margin-bottom:8px'>&#127860; Order Snacks (Optional)</div>"
            "<input type='text' id='snk-" + vid + "' placeholder='e.g. Biscuits, Namkeen, Fruits...' style='width:100%;padding:8px;border:1.5px solid #ddd;border-radius:6px;font-size:13px'>"
            "</div>"

            "<button onclick='confirmOrder(\"" + vid + "\",\"" + str(v["name"]) + "\",\"" + name + "\")' "
            "style='background:#1565C0;color:white;border:none;padding:10px 20px;border-radius:8px;cursor:pointer;font-weight:700;font-size:14px;width:100%'>"
            "&#9749; Confirm Order</button>"
            "</div>"
        )
    if not active_rows:
        active_rows = "<div style='text-align:center;padding:30px;color:#999'>No active visitors at the moment</div>"

    hist_rows = ""
    for v in all_visitors:
        bc = "pending" if v["status"]=="pending" else ("approved" if v["status"]=="approved" else "rejected")
        ab = ""
        if v["status"] == "pending":
            ab += '<button class="btn ba" onclick="act('+str(v["id"])+',' + "'approve'" + ')">&#10003; Approve</button>'
            ab += '<button class="btn br" onclick="act('+str(v["id"])+',' + "'reject'" + ')">&#10005; Reject</button>'
        co = v.get("checkout_at") or "-"
        hist_rows += (
            "<tr><td><strong>" + str(v["name"]) + "</strong></td>"
            "<td>" + str(v["phone"]) + "</td>"
            "<td>" + str(v["purpose"]) + "</td>"
            "<td style='font-size:11px'>" + str(v["created_at"]) + "</td>"
            "<td style='font-size:11px'>" + co + "</td>"
            "<td><span class='badge " + bc + "'>" + v["status"].upper() + "</span></td>"
            "<td>" + ab + "</td></tr>"
        )
    if not hist_rows:
        hist_rows = '<tr><td colspan="7" style="text-align:center;padding:20px;color:#999">No visitors</td></tr>'

    return (
        "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>" + name + " Dashboard</title>"
        "<style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:Arial;background:#f0f4f8}"
        ".header{background:#1565C0;color:white;padding:13px 25px;display:flex;justify-content:space-between;align-items:center}"
        ".header a{color:white;text-decoration:none;background:rgba(255,255,255,0.2);padding:7px 13px;border-radius:5px;font-size:13px;margin-left:7px}"
        ".container{max-width:900px;margin:20px auto;padding:0 15px}"
        ".card{background:white;border-radius:9px;padding:18px;box-shadow:0 2px 8px rgba(0,0,0,0.07);margin-bottom:15px}"
        ".card h3{color:#1565C0;margin-bottom:14px}"
        "table{width:100%;border-collapse:collapse}"
        "th{background:#1565C0;color:white;padding:10px;font-size:12px;text-align:left}"
        "td{padding:10px;border-bottom:1px solid #eee;font-size:13px;vertical-align:middle}"
        ".badge{display:inline-block;padding:3px 9px;border-radius:11px;font-size:11px;font-weight:700}"
        ".badge.pending{background:#FFF8E1;color:#F57F17}"
        ".badge.approved{background:#E8F5E9;color:#2E7D32}"
        ".badge.rejected{background:#FFEBEE;color:#C62828}"
        ".btn{padding:5px 11px;border:none;border-radius:5px;cursor:pointer;font-size:12px;font-weight:600;margin:2px}"
        ".ba{background:#2E7D32;color:white}.br{background:#C62828;color:white}"
        "</style></head><body>"
        "<div class='header'><h1>" + name + " — Dashboard</h1>"
        "<div><a href='/'>Visitor Form</a><a href='/employee-logout'>Logout</a></div></div>"
        "<div class='container'>"
        "<div class='card'><h3>&#128100; Active Visitors</h3>" + active_rows + "</div>"
        "<div class='card'><h3>&#128203; Visitor History</h3>"
        "<table><tr><th>Name</th><th>Phone</th><th>Purpose</th><th>In Time</th><th>Out Time</th><th>Status</th><th>Action</th></tr>"
        + hist_rows + "</table></div></div>"
        "<script>"
        "var _qty={};"
        "function changeQty(vid,delta){"
        "if(!_qty[vid])_qty[vid]=1;"
        "_qty[vid]=Math.max(1,_qty[vid]+delta);"
        "document.getElementById('qty-'+vid).textContent=_qty[vid];}"
        "async function confirmOrder(vid,vname,person){"
        "var drink=document.getElementById('drk-'+vid).value;"
        "var qty=_qty[vid]||1;"
        "var note=document.getElementById('note-'+vid).value;"
        "var snacks=document.getElementById('snk-'+vid).value;"
        "if(!drink){alert('Please select a drink first!');return;}"
        "var r=await fetch('/api/beverage',{method:'POST',headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify({visitor_id:vid,visitor_name:vname,person_to_meet:person,drink:drink,quantity:qty,note:note,snacks:snacks})});"
        "var d=await r.json();"
        "if(d.success){alert('Order sent to Pantry!');location.reload();}}"
        "async function act(id,action){"
        "if(!confirm(action+' this visitor?'))return;"
        "var r=await fetch('/action/'+id+'/'+action,{headers:{'Accept':'application/json'}});"
        "var d=await r.json();"
        "if(action==='approve'){window.open('/pass/'+id);}"
        "location.reload();}"
        "async function checkout(id){"
        "if(!confirm('Checkout visitor?'))return;"
        "await fetch('/api/checkout/'+id,{method:'POST'});"
        "location.reload();}"
        "var _pc=0;"
        "async function checkNew(){try{"
        "var r=await fetch('/api/pending-count');var d=await r.json();"
        "if(_pc>0&&d.count>_pc){_beep();}"
        "_pc=d.count;document.title=d.count>0?'('+d.count+') New - '+'" + name + "':'"+name+" Dashboard';"
        "}catch(e){}}"
        "function _beep(){"
        "try{var c=new(window.AudioContext||window.webkitAudioContext)();"
        "var notes=[880,660,880,1100];"
        "notes.forEach(function(freq,i){"
        "var o=c.createOscillator(),g=c.createGain();"
        "o.connect(g);g.connect(c.destination);"
        "o.frequency.value=freq;o.type='sine';"
        "var t=c.currentTime+i*0.2;"
        "g.gain.setValueAtTime(0,t);"
        "g.gain.linearRampToValueAtTime(1.5,t+0.05);"
        "g.gain.exponentialRampToValueAtTime(0.001,t+0.35);"
        "o.start(t);o.stop(t+0.35);});"
        "}catch(e){}}"
        "setInterval(checkNew,8000);"
        "</script></body></html>"
    )

@app.route("/employee-logout")
def employee_logout():
    session.clear()
    return redirect("/employee-login")

@app.route("/manifest.json")
def manifest():
    return jsonify({
        "name": "Maxwell Visitor Management",
        "short_name": "Maxwell VM",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#f0f4f8",
        "theme_color": "#1565C0"
    })

init_db()

if __name__ == "__main__":
    init_db()
    print("\n" + "="*55)
    print("  Maxwell Engineering Solutions - Visitor System v2.0")
    print("="*55)
    print("  App:    http://localhost:5000")
    print("  Admin:  http://localhost:5000/admin  PIN: 1234")
    print("  Pantry: http://localhost:5000/pantry")
    print("="*55 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
