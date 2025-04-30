from io import BytesIO
import json
import os
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
import matplotlib.pyplot as plt
import networkx as nx
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import mysql
import pywifi

from main.utils import send_network_report_email
from .db import get_db
import matplotlib.image as mpimg
from django.views.decorators.csrf import csrf_exempt
import os
import time
import random
import threading


def register(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        role = request.POST.get('role', 'user')

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (email, password, role) VALUES (%s, %s, %s)", (email, password, role))
            conn.commit()
            messages.success(request, 'Registered successfully.')
            return redirect('login')
        except mysql.connector.IntegrityError:
            messages.error(request, 'Email already exists.')
        finally:
            cursor.close()
            conn.close()

    return render(request, 'register.html')

def login_view(request):
    # Redirect logged-in users
    if request.session.get('user_id'):
        role = request.session.get('role')
        if role == 'admin':
            return redirect('admin_dashboard')
        elif role == 'user':
            return redirect('user_dashboard')

    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            request.session['user_id'] = user['id']
            request.session['role'] = user['role']
            request.session['email'] = user['email']

            if user['role'] == 'admin':
                return redirect('admin_dashboard')
            else:
                return redirect('user_dashboard')
        else:
            messages.error(request, 'Invalid credentials.')

    return render(request, 'login.html')


def admin_dashboard(request):
    if not request.session.get('user_id') or request.session.get('role') != 'admin':
        return redirect('login')

    json_path = os.path.join(os.path.dirname(__file__), 'network_data.json')
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    branches = data['branches']
    admin_email = request.session['email']

    return render(request, 'admin_dashboard.html', {'branches': branches, 'admin_email': admin_email})


# For Topology Details
def admin_cards(request):
    if not request.session.get('user_id') or request.session.get('role') != 'admin':
        return redirect('login')

    json_path = os.path.join(os.path.dirname(__file__), 'network_data.json')
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    branches = data['branches']
    admin_email = request.session['email']

    return render(request, 'cards.html', {'branches': branches, 'admin_email': admin_email})

# For Topology Details
def user_cards(request):
    if not request.session.get('user_id'):
        return redirect('login')

    json_path = os.path.join(os.path.dirname(__file__), 'network_data.json')
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    branches = data['branches']
    admin_email = request.session['email']

    return render(request, 'user_cards.html', {'branches': branches, 'admin_email': admin_email})

# For Managing User Access
def access(request):
    if not request.session.get('user_id') or request.session.get('role') != 'admin':
        return redirect('login')

    json_path = os.path.join(os.path.dirname(__file__), 'network_data.json')
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    branches = data['branches']
    admin_email = request.session['email']

    return render(request, 'access_management.html', {'branches': branches, 'admin_email': admin_email})

# For Viewing Uptime Graph
def uptime(request):
    if not request.session.get('user_id') or request.session.get('role') != 'admin':
        return redirect('login')

    json_path = os.path.join(os.path.dirname(__file__), 'network_data.json')
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    branches = data['branches']
    admin_email = request.session['email']

    return render(request, 'uptime.html', {'branches': branches, 'admin_email': admin_email})


# For Viewing Uptime Graph
def User_Uptime(request):
    if not request.session.get('user_id') or request.session.get('role') != 'admin':
        return redirect('login')

    json_path = os.path.join(os.path.dirname(__file__), 'network_data.json')
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    branches = data['branches']
    admin_email = request.session['email']

    return render(request, 'User_Uptime.html', {'branches': branches, 'admin_email': admin_email})


# For Email Notification
def notify(request):
    if not request.session.get('user_id') or request.session.get('role') != 'admin':
        return redirect('login')

    json_path = os.path.join(os.path.dirname(__file__), 'network_data.json')
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    branches = data['branches']
    admin_email = request.session['email']

    return render(request, 'notify.html', {'branches': branches, 'admin_email': admin_email})


# Send branches data
def network_data_api(request):
    if not request.session.get('user_id'):
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    user_id = request.session.get('user_id')
    user_role = request.session.get('role')  # Assuming 'role' is stored in session

    json_path = os.path.join(os.path.dirname(__file__), 'network_data.json')
    with open(json_path, 'r') as f:
        data = json.load(f)

    # If user is not an admin, filter branches based on user_access
    if user_role != 'admin':
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT branch_name FROM user_access WHERE user_id = %s", (user_id,))
        allowed_branches = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()

        branches = [branch for branch in data['branches'] if branch['branchname'] in allowed_branches]
    else:
        branches = data['branches']

    return JsonResponse({'branches': branches})


# Map email -> (thread, stop_event)
scheduled_tasks = {}

# Send Auto Emails
@csrf_exempt
def schedule_email(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            email = data["email"]
            interval = int(data["time_interval"])

            # Cancel existing schedule if exists
            if email in scheduled_tasks:
                old_thread, stop_event = scheduled_tasks[email]
                stop_event.set()  # Signal the thread to stop

            # Send email immediately
            send_network_report_email(email)

            # Create a new stop event for the new thread
            stop_event = threading.Event()

            def scheduler():
                while not stop_event.is_set():
                    time.sleep(interval * 3600)
                    if not stop_event.is_set():
                        send_network_report_email(email)

            thread = threading.Thread(target=scheduler, daemon=True)
            thread.start()

            scheduled_tasks[email] = (thread, stop_event)

            return JsonResponse({"status": "success", "message": f"Email scheduled for {email} every {interval} hour(s)."})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    else:
        return JsonResponse({"status": "error", "message": "Invalid request method."})


def user_dashboard(request):
    if not request.session.get('user_id') or request.session.get('role') != 'user':
        return redirect('login')

    # Get user_id from session
    user_id = request.session['user_id']

    # Load all branches from network_data.json
    json_path = os.path.join(os.path.dirname(__file__), 'network_data.json')
    with open(json_path, 'r') as f:
        data = json.load(f)

    # Query user_access table to get branches the user has access to
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT branch_name FROM user_access WHERE user_id = %s", (user_id,))
    allowed_branches = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()

    # Filter branches to only those the user has access to
    branches = [branch for branch in data['branches'] if branch['branchname'] in allowed_branches]
    user_email = request.session['email']

    return render(request, 'user_dashboard.html', {'branches': branches, 'user_email': user_email})

@csrf_exempt
def manage_network_data(request):
    if not request.session.get('user_id') or request.session.get('role') != 'admin':
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        # Debug: print raw request body
        print("Raw request body:", request.body.decode('utf-8'))

        data = json.loads(request.body)

        # Debug: print parsed JSON
        print("Parsed JSON data:", data)

        action = data.get('action')
        if not action:
            return JsonResponse({'error': 'Missing action field'}, status=400)

        json_path = os.path.join(os.path.dirname(__file__), 'network_data.json')

        # Load current network data
        with open(json_path, 'r') as f:
            network_data = json.load(f)

        if action == 'add':
            entry_type = data.get('type')

            # 👇 Smart inference for devices (e.g., "type": "router" becomes device)
            if entry_type not in ['branch', 'server', 'device'] and 'devicename' in data and 'servername' in data:
                entry_type = 'device'
                data['device_type'] = data.get('type')  # e.g., router
                print("Inferred device type:", data['device_type'])

            if not entry_type:
                return JsonResponse({'error': 'Missing type for add action'}, status=400)

            if entry_type == 'branch':
                if not data.get('branchname'):
                    return JsonResponse({'error': 'Missing branchname'}, status=400)

                new_branch = {
                    'branchname': data['branchname'],
                    'servers': []
                }
                network_data['branches'].append(new_branch)

            elif entry_type == 'server':
                branchname = data.get('branchname')
                if not branchname or not data.get('servername') or not data.get('ip'):
                    return JsonResponse({'error': 'Missing server fields (branchname, servername, ip)'}, status=400)

                branch = next((b for b in network_data['branches'] if b['branchname'] == branchname), None)
                if not branch:
                    return JsonResponse({'error': 'Branch not found'}, status=404)

                new_server = {
                    'servername': data['servername'],
                    'ip': data['ip'],
                    'cpu_usage': data.get('cpu_usage', '0%'),
                    'ram_usage': data.get('ram_usage', '0%'),
                    'latency': data.get('latency', '0ms'),
                    'bandwidth': data.get('bandwidth', '0Mbps'),
                    'devices': []
                }
                branch['servers'].append(new_server)

            elif entry_type == 'device':
                branchname = data.get('branchname')
                servername = data.get('servername')
                if not branchname or not servername or not data.get('devicename') or not data.get('device_type'):
                    return JsonResponse({'error': 'Missing device fields'}, status=400)

                branch = next((b for b in network_data['branches'] if b['branchname'] == branchname), None)
                if not branch:
                    return JsonResponse({'error': 'Branch not found'}, status=404)

                server = next((s for s in branch['servers'] if s['servername'] == servername), None)
                if not server:
                    return JsonResponse({'error': 'Server not found'}, status=404)

                new_device = {
                    'devicename': data['devicename'],
                    'type': data['device_type']  # This is now cleanly separated
                }
                server['devices'].append(new_device)

            else:
                return JsonResponse({'error': 'Invalid entry type'}, status=400)

        elif action == 'edit':
            branchname = data.get('branchname')
            servername = data.get('servername')
            if not branchname or not servername:
                return JsonResponse({'error': 'Missing branchname or servername for edit'}, status=400)

            branch = next((b for b in network_data['branches'] if b['branchname'] == branchname), None)
            if not branch:
                return JsonResponse({'error': 'Branch not found'}, status=404)

            server = next((s for s in branch['servers'] if s['servername'] == servername), None)
            if not server:
                return JsonResponse({'error': 'Server not found'}, status=404)

            server['ip'] = data.get('ip', server['ip'])
            server['cpu_usage'] = data.get('cpu_usage', server['cpu_usage'])
            server['ram_usage'] = data.get('ram_usage', server['ram_usage'])
            server['latency'] = data.get('latency', server['latency'])
            server['bandwidth'] = data.get('bandwidth', server['bandwidth'])

            if 'devices' in data:
                server['devices'] = data['devices']

        elif action == 'delete':
            branchname = data.get('branchname')
            servername = data.get('servername')
            if not branchname or not servername:
                return JsonResponse({'error': 'Missing branchname or servername for delete'}, status=400)

            branch = next((b for b in network_data['branches'] if b['branchname'] == branchname), None)
            if not branch:
                return JsonResponse({'error': 'Branch not found'}, status=404)

            server = next((s for s in branch['servers'] if s['servername'] == servername), None)
            if not server:
                return JsonResponse({'error': 'Server not found'}, status=404)

            branch['servers'].remove(server)

        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)

        # Save updated data
        with open(json_path, 'w') as f:
            json.dump(network_data, f, indent=2)

        return JsonResponse({'message': f'{action.capitalize()} successful'})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print("Exception occurred:", str(e))  # Debug log
        return JsonResponse({'error': str(e)}, status=500)
    

def logout_view(request):
    request.session.flush()
    return redirect('login')

@csrf_exempt
def manage_user_access(request):
    # Ensure only admins can access this view
    if not request.session.get('user_id') or request.session.get('role') != 'admin':
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    # Load branches from network_data.json
    json_path = os.path.join(os.path.dirname(__file__), 'network_data.json')
    with open(json_path, 'r') as f:
        data = json.load(f)
    branches = [branch['branchname'] for branch in data['branches']]

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'GET':
        # Fetch all users
        cursor.execute("SELECT id, email, role FROM users")
        users = cursor.fetchall()

        # Fetch current user access mappings
        cursor.execute("SELECT user_id, branch_name FROM user_access")
        user_access = cursor.fetchall()

        # Organize access data by user
        access_by_user = {}
        for access in user_access:
            user_id = access['user_id']
            if user_id not in access_by_user:
                access_by_user[user_id] = []
            access_by_user[user_id].append(access['branch_name'])

        # Prepare response
        response = {
            'users': [
                {
                    'id': user['id'],
                    'email': user['email'],
                    'role': user['role'],
                    'branches': access_by_user.get(user['id'], [])
                } for user in users
            ],
            'branches': branches
        }
        cursor.close()
        conn.close()
        return JsonResponse(response)

    elif request.method == 'POST':
        try:
            # Parse JSON body
            data = json.loads(request.body)
            user_id = data.get('user_id')
            branch_names = data.get('branches', [])

            # Validate input
            if not user_id or not isinstance(branch_names, list):
                return JsonResponse({'error': 'Invalid input'}, status=400)

            # Verify user exists
            cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cursor.fetchone():
                return JsonResponse({'error': 'User not found'}, status=404)

            # Verify all branch names are valid
            invalid_branches = [b for b in branch_names if b not in branches]
            if invalid_branches:
                return JsonResponse({'error': f'Invalid branches: {invalid_branches}'}, status=400)

            # Clear existing access for the user
            cursor.execute("DELETE FROM user_access WHERE user_id = %s", (user_id,))
            
            # Insert new access entries
            for branch_name in branch_names:
                cursor.execute(
                    "INSERT INTO user_access (user_id, branch_name) VALUES (%s, %s)",
                    (user_id, branch_name)
                )
            
            conn.commit()
            cursor.close()
            conn.close()
            return JsonResponse({'message': 'User access updated successfully'})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    else:
        cursor.close()
        conn.close()
        return JsonResponse({'error': 'Method not allowed'}, status=405)


# Function to load the JSON data from a file
def load_data(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# Function to plot the topology for a specific branch and server
def plot_topology(data, branch_name, server_name):
    # Create the graph
    G = nx.Graph()

    # Define the icon paths for server and device
    current_directory = os.path.dirname(__file__)  # Get the current directory where the view is located
    icon_paths = {
        "server": os.path.join(current_directory, "server.png"),  # Icon for servers
        "device": os.path.join(current_directory, "device.png")   # Icon for devices (router, switch, etc.)
    }

    # Find the specific branch and server
    for branch in data["branches"]:
        if branch["branchname"] == branch_name:
            for server in branch["servers"]:
                if server["servername"] == server_name:
                    # Add the server to the graph
                    G.add_node(server["servername"], type="server", ip=server["ip"], cpu_usage=server["cpu_usage"], ram_usage=server["ram_usage"])

                    # Add the devices connected to the server
                    for device in server["devices"]:
                        device_name = device["devicename"]
                        G.add_node(device_name, type="device", ip=device["ip"])
                        G.add_edge(server["servername"], device_name)
                    break
            break

    # Dynamically create shell layout groups
    pos = nx.spring_layout(G, seed=42)  # Using spring layout for more even distribution

    # Function to draw images and labels dynamically
    def draw_node_images_with_labels(G, pos, ax, icon_paths):
        for node in G.nodes:
            node_type = G.nodes[node]['type']
            # Use server icon for servers, and device icon for all devices
            icon_path = icon_paths["server"] if node_type == "server" else icon_paths["device"]
            img = mpimg.imread(icon_path)
            imagebox = OffsetImage(img, zoom=0.1)
            ab = AnnotationBbox(imagebox, pos[node], frameon=False)
            ax.add_artist(ab)

            # Adjust label position based on the node type (server or device)
            label_offset = -0.20
            if node_type == "server":
                label_offset = -0.60  # More space below for servers
            ax.text(
                pos[node][0],
                pos[node][1] + label_offset,  # Place label below the node
                node,
                ha='center',
                va='top',
                fontsize=10,
                fontweight='bold'
            )

    # Plot the graph
    fig, ax = plt.subplots()
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color='gray')
    draw_node_images_with_labels(G, pos, ax, icon_paths)

    plt.title(f"Network Topology for {branch_name} - {server_name}", fontsize=14)
    plt.axis('off')
    plt.tight_layout()

    # Save the plot to a BytesIO object
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format="png")
    img_buffer.seek(0)

    return img_buffer

# Django view to handle the request
def plot_topology_view(request):
    # Get the branch name and server name from the GET request
    branch_name = request.GET.get('branch_name')
    server_name = request.GET.get('server_name')

    if not branch_name or not server_name:
        return HttpResponse("Missing parameters", status=400)

    # Load the JSON data from the file
    data = json.load(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'network_data.json')))

    # Generate the plot and get the image buffer
    img_buffer = plot_topology(data, branch_name, server_name)

    # Return the image in the response
    return HttpResponse(img_buffer, content_type='image/png')


def NetworkSimulation():
    # Path to network_data.json
    json_path = os.path.join(os.path.dirname(__file__), 'network_data.json')

    # Dictionary to track trends for each server (to simulate gradual changes)
    server_trends = {}

    while True:
        try:
            # Read the current JSON data
            with open(json_path, 'r') as f:
                data = json.load(f)

            # Process each branch and server
            for branch in data['branches']:
                for server in branch['servers']:
                    server_key = f"{branch['branchname']}_{server['servername']}"

                    # Initialize trends for this server if not already set
                    if server_key not in server_trends:
                        server_trends[server_key] = {
                            'cpu_base': random.randint(40, 60),
                            'ram_base': random.randint(50, 70),
                            'latency_base': random.randint(10, 30),
                            'bandwidth_base': random.randint(100, 300),
                            'cpu_direction': 1,
                            'ram_direction': 1,
                            'latency_direction': 1,
                            'bandwidth_direction': 1
                        }

                    # Assign missing IPs to devices
                    subnet_base = '.'.join(server['ip'].split('.')[:3]) + '.'
                    used_ips = {server['ip']}
                    for device in server['devices']:
                        if 'ip' in device:
                            used_ips.add(device['ip'])

                    next_ip_suffix = 4
                    for device in server['devices']:
                        if 'ip' not in device:
                            # Find the next available IP in the subnet
                            while f"{subnet_base}{next_ip_suffix}" in used_ips and next_ip_suffix < 255:
                                next_ip_suffix += 1
                            if next_ip_suffix < 255:
                                new_ip = f"{subnet_base}{next_ip_suffix}"
                                device['ip'] = new_ip
                                used_ips.add(new_ip)

                    trends = server_trends[server_key]

                    # Update CPU usage (10-90%)
                    trends['cpu_base'] += trends['cpu_direction'] * random.uniform(0.5, 2.0)
                    if trends['cpu_base'] > 80:
                        trends['cpu_direction'] = -1
                    elif trends['cpu_base'] < 20:
                        trends['cpu_direction'] = 1
                    cpu_usage = max(10, min(90, int(trends['cpu_base'] + random.uniform(-5, 5))))
                    server['cpu_usage'] = f"{cpu_usage}%"

                    # Update RAM usage (20-95%)
                    trends['ram_base'] += trends['ram_direction'] * random.uniform(0.5, 2.0)
                    if trends['ram_base'] > 90:
                        trends['ram_direction'] = -1
                    elif trends['ram_base'] < 30:
                        trends['ram_direction'] = 1
                    ram_usage = max(20, min(95, int(trends['ram_base'] + random.uniform(-5, 5))))
                    server['ram_usage'] = f"{ram_usage}%"

                    # Update latency (5-50ms)
                    trends['latency_base'] += trends['latency_direction'] * random.uniform(0.2, 1.0)
                    if trends['latency_base'] > 45:
                        trends['latency_direction'] = -1
                    elif trends['latency_base'] < 10:
                        trends['latency_direction'] = 1
                    latency = max(5, min(50, int(trends['latency_base'] + random.uniform(-2, 2))))
                    server['latency'] = f"{latency}ms"

                    # Update bandwidth (50-500Mbps)
                    trends['bandwidth_base'] += trends['bandwidth_direction'] * random.uniform(5, 20)
                    if trends['bandwidth_base'] > 450:
                        trends['bandwidth_direction'] = -1
                    elif trends['bandwidth_base'] < 100:
                        trends['bandwidth_direction'] = 1
                    bandwidth = max(50, min(500, int(trends['bandwidth_base'] + random.uniform(-10, 10))))
                    server['bandwidth'] = f"{bandwidth}Mbps"

            # Write updated data back to the file
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"Error updating network_data.json: {e}")

        # Wait for 3 seconds before the next update
        time.sleep(3)

thread = threading.Thread(target=NetworkSimulation, daemon=True)
thread.start()

# Path to the existing JSON file
NETWORK_DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'network_data.json')

# Function to update or add new branches, servers, and devices
def merge_network_data(existing_data, new_data):
    for branch in new_data.get('branches', []):
        branch_exists = False
        # Check if branch already exists
        for existing_branch in existing_data['branches']:
            if existing_branch['branchname'] == branch['branchname']:
                branch_exists = True
                # If the branch exists, update servers or add new ones
                for server in branch.get('servers', []):
                    server_exists = False
                    for existing_server in existing_branch.get('servers', []):
                        if existing_server['servername'] == server['servername']:
                            server_exists = True
                            # Update the existing server with new data
                            if 'devices' in server:
                                # Avoid duplicates: add new devices only
                                existing_server['devices'].extend(device for device in server['devices']
                                                                   if device not in existing_server['devices'])
                            break
                    # If server doesn't exist, add it
                    if not server_exists:
                        existing_branch['servers'].append(server)
                break
        # If branch doesn't exist, add the new branch with servers
        if not branch_exists:
            existing_data['branches'].append(branch)

    return existing_data

@csrf_exempt
def update_network_data(request):
    if request.method == 'POST':
        try:
            # Check if the file is included in the request
            if 'jsonFile' not in request.FILES:
                return JsonResponse({"error": "No file uploaded."}, status=400)

            # Get the uploaded file
            json_file = request.FILES['jsonFile']

            # Read the file content
            file_content = json_file.read().decode('utf-8')

            # Parse the JSON content
            try:
                new_data = json.loads(file_content)
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON data."}, status=400)

            # Load existing data from network_data.json
            with open(NETWORK_DATA_FILE, 'r') as f:
                existing_data = json.load(f)

            # Update the existing data with the new data using merge_network_data
            updated_data = merge_network_data(existing_data, new_data)

            # Save the updated data back to the JSON file
            with open(NETWORK_DATA_FILE, 'w') as f:
                json.dump(updated_data, f, indent=4)

            return JsonResponse({"message": "Network data updated successfully"}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Only POST method is allowed"}, status=405)

def get_uptime_data(request, range_type='7d'):
    days = 7 if range_type == '7d' else 30
    branch_filter = request.GET.get('branch', 'all')

    json_path = os.path.join(os.path.dirname(__file__), 'network_data.json')
    with open(json_path, 'r') as f:
        data = json.load(f)

    uptime_data = {}
    branches = []

    for branch in data['branches']:
        branch_name = branch['branchname']
        branches.append(branch_name)

        if branch_filter != 'all' and branch_filter != branch_name:
            continue

        for server in branch['servers']:
            uptime_data[server['servername']] = [round(random.uniform(95, 100), 2) for _ in range(days)]

    return JsonResponse({'uptime': uptime_data, 'branches': branches})

# Gather Near Networks
def update_network_data_with_home_branch():
    # Get the absolute path to the directory where this script resides
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(script_dir, 'network_data.json')

    # Load the existing data
    if not os.path.exists(json_file):
        raise FileNotFoundError(f"{json_file} not found.")

    with open(json_file, 'r') as file:
        data = json.load(file)

    # Scan for nearby WiFi Access Points
    wifi = pywifi.PyWiFi()
    iface = wifi.interfaces()[0]
    iface.scan()
    time.sleep(2)  # Wait for the scan to complete
    results = iface.scan_results()

    # Possible device types
    device_types = ["access_point", "router", "switch", "firewall"]

    # Prepare device list with random types (limit to 10 devices)
    devices = []
    seen_ssids = set()
    for ap in results:
        if ap.ssid and ap.ssid not in seen_ssids:
            seen_ssids.add(ap.ssid)
            devices.append({
                "devicename": ap.ssid,
                "type": random.choice(device_types)
            })
        if len(devices) >= 10:
            break  # Limit to 10 devices

    # Construct the Home branch
    home_branch = {
        "branchname": "Home",
        "servers": [
            {
                "servername": "Local-Server",
                "ip": "192.168.0.100",
                "cpu_usage": "25%",
                "ram_usage": "40%",
                "latency": "10ms",
                "bandwidth": "500Mbps",
                "devices": devices
            }
        ]
    }

    # Remove the previous "Home" branch if it exists
    data["branches"] = [b for b in data["branches"] if b["branchname"] != "Home"]
    
    # Add the updated "Home" branch
    data["branches"].append(home_branch)

    # Save back the updated JSON
    with open(json_file, 'w') as file:
        json.dump(data, file, indent=2)

    print("Home branch updated successfully.")

# Run the function
update_network_data_with_home_branch()