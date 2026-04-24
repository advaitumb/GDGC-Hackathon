import os, base64, subprocess, shutil, time, json
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from cryptography.fernet import Fernet

app = Flask(__name__)
CORS(app)

# Folders
UPLOAD_DIR = 'uploads'
VAULT_DIR = 'vault'
KEY_DIR = 'secure_keys'      # Folder for passwords
MASTER_DIR = 'final_stream'   # Permanent storage

for d in [UPLOAD_DIR, VAULT_DIR, KEY_DIR, MASTER_DIR]:
    os.makedirs(d, exist_ok=True)

def clear_folder(folder_path):
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path): os.unlink(file_path)

# --- NEW: DIFFERENT URL FOR KEYS ---
@app.route('/get_keys', methods=['GET'])
def get_keys():
    keys = {}
    for filename in os.listdir(KEY_DIR):
        with open(os.path.join(KEY_DIR, filename), 'r') as f:
            keys[filename.replace('.key', '')] = f.read()
    return jsonify(keys)

@app.route('/sender_upload', methods=['POST'])
def sender():
    if 'video' not in request.files: return "No file", 400
    
    # Clear temporary areas for new set
    clear_folder(UPLOAD_DIR)
    clear_folder(VAULT_DIR)
    clear_folder(KEY_DIR)
    
    file = request.files['video']
    video_path = os.path.join(UPLOAD_DIR, file.filename)
    file.save(video_path)

    # 1. Chunking
    subprocess.run(f'.\\ffmpeg.exe -i "{video_path}" -f segment -segment_time 30 -c copy "{UPLOAD_DIR}/part_%03d.mp4"', shell=True)

    # 2. Encrypt & Save Keys separately
    for filename in sorted(os.listdir(UPLOAD_DIR)):
        if filename.startswith("part_") and filename.endswith(".mp4"):
            chunk_key = Fernet.generate_key()
            
            # Save Key to DIFFERENT FOLDER
            with open(os.path.join(KEY_DIR, f"{filename}.key"), "w") as kf:
                kf.write(chunk_key.decode())

            # Encrypt Chunk
            with open(os.path.join(UPLOAD_DIR, filename), "rb") as f:
                encrypted_data = Fernet(chunk_key).encrypt(f.read())
            
            with open(os.path.join(VAULT_DIR, f"{filename}.dat"), "wb") as f:
                f.write(encrypted_data)

    return jsonify({"status": "Transmitted", "msg": "Chunks in Vault, Keys in Secure_Keys folder"})

@app.route('/receiver_assemble', methods=['POST'])
def receiver():
    # 1. Fetch Keys from the "Different URL" logic (simulated here)
    # In a real app, the frontend would fetch /get_keys first.
    vault_files = sorted([f for f in os.listdir(VAULT_DIR) if f.endswith('.dat')])
    if not vault_files: return "Nothing to sync", 400

    temp_decrypted = []
    
    for filename in vault_files:
        chunk_id = filename.replace(".dat", "")
        key_path = os.path.join(KEY_DIR, f"{chunk_id}.key")
        
        with open(key_path, "r") as kf:
            chunk_key = kf.read().encode()
        
        with open(os.path.join(VAULT_DIR, filename), "rb") as f:
            data = Fernet(chunk_key).decrypt(f.read())
        
        out_path = os.path.join(MASTER_DIR, f"temp_{chunk_id}.mp4")
        with open(out_path, "wb") as f:
            f.write(data)
        temp_decrypted.append(out_path)

    # 2. GRADUAL INTEGRATION (The "Merge")
    master_file = os.path.join(MASTER_DIR, "Master_Broadcast.mp4")
    
    if not os.path.exists(master_file):
        # If first time, just rename the first temp chunk as master
        # (Simplified for demo: joining all current temps)
        list_path = os.path.join(MASTER_DIR, 'list.txt')
        with open(list_path, 'w') as f:
            for p in temp_decrypted: f.write(f"file '{os.path.abspath(p).replace('\\', '/')}'\n")
        subprocess.run(f'.\\ffmpeg.exe -f concat -safe 0 -i "{list_path}" -c copy -y "{master_file}"', shell=True)
    else:
        # APPEND logic: Merge Master + New Temps into a "New_Master", then replace
        new_master = os.path.join(MASTER_DIR, "New_Master.mp4")
        list_path = os.path.join(MASTER_DIR, 'list.txt')
        with open(list_path, 'w') as f:
            f.write(f"file '{os.path.abspath(master_file).replace('\\', '/')}'\n")
            for p in temp_decrypted: f.write(f"file '{os.path.abspath(p).replace('\\', '/')}'\n")
        
        subprocess.run(f'.\\ffmpeg.exe -f concat -safe 0 -i "{list_path}" -c copy -y "{new_master}"', shell=True)
        os.remove(master_file)
        os.rename(new_master, master_file)

    # 3. AUTO-DELETE CHUNKS AND KEYS
    for p in temp_decrypted: os.remove(p)
    clear_folder(VAULT_DIR)
    clear_folder(KEY_DIR)

    return jsonify({"status": "Master Updated", "file": "Master_Broadcast.mp4"})

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    # host='0.0.0.0' makes it accessible on your Wi-Fi network
    app.run(host='0.0.0.0', port=5000, debug=True)