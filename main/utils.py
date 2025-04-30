# utils.py
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
from pathlib import Path

def send_network_report_email(recipient_email):
    # Load the JSON file from the same directory as this file
    json_path = Path(__file__).resolve().parent / "network_data.json"
    with open(json_path, "r") as f:
        network_data = json.load(f)

    # Build the modern HTML email
    html = """
    <html>
    <head>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f4f4f7;
                color: #333;
                padding: 20px;
                line-height: 1.6;
            }
            .container {
                background-color: #ffffff;
                border-radius: 8px;
                padding: 20px;
                max-width: 800px;
                margin: auto;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }
            h2 {
                color: #0056b3;
                border-bottom: 2px solid #e0e0e0;
                padding-bottom: 10px;
            }
            h3 {
                color: #007bff;
                margin-top: 30px;
                border-bottom: 1px solid #ddd;
                padding-bottom: 5px;
            }
            .server {
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 10px 15px;
                margin-bottom: 15px;
            }
            .server strong {
                display: inline-block;
                width: 100px;
            }
            ul {
                padding-left: 20px;
                margin: 8px 0;
            }
            li {
                margin-bottom: 4px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🌐 Daily Network Status Report</h2>
    """

    for branch in network_data["branches"]:
        html += f"<h3>🏢 {branch['branchname']}</h3>"
        for server in branch["servers"]:
            html += f"""
            <div class="server">
                <p><strong>Server:</strong> {server['servername']}</p>
                <p><strong>IP:</strong> {server['ip']}</p>
                <p><strong>CPU:</strong> {server['cpu_usage']} &nbsp;&nbsp; <strong>RAM:</strong> {server['ram_usage']}</p>
                <p><strong>Latency:</strong> {server['latency']} &nbsp;&nbsp; <strong>Bandwidth:</strong> {server['bandwidth']}</p>
                <p><strong>Devices:</strong></p>
                <ul>
            """
            for device in server["devices"]:
                html += f"<li>🖥 {device['devicename']} ({device['type']}, {device['ip']})</li>"
            html += "</ul></div>"

    html += """
        </div>
    </body>
    </html>
    """

    # Email sending setup
    username = "5de44d001@smtp-brevo.com"
    password = "a5IkKV9cCpvsfXEM"
    smtp_server = "smtp-relay.brevo.com"
    smtp_port = 587

    msg = MIMEMultipart()
    msg['From'] = f"Network Monitor <{username}>"
    msg['To'] = recipient_email
    msg['Subject'] = "Daily Network Report"

    msg.attach(MIMEText(html, 'html'))

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(username, password)
        server.sendmail(username, recipient_email, msg.as_string())
