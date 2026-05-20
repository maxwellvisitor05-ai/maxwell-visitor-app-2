#!/usr/bin/env python3
"""Maxwell Engineering Solutions - Visitor Management System v2.0"""

from flask import Flask, request, jsonify, redirect, session, send_file
import sqlite3, base64, io, threading, os
from datetime import datetime, timezone, timedelta
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

BEEP_JS = """
function _beep(n){
  try{
    var c=new(window.AudioContext||window.webkitAudioContext)();
    var f=[880,660,880,1100,880,660,880];
    for(var i=0;i<(n||4);i++){(function(x){
      var o=c.createOscillator(),g=c.createGain();
