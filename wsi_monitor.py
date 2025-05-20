import os
import time
from datetime import datetime
from plyer import notification


FOLDER_TO_WATCH = r"C:/Users/PC/Desktop/digital_pathology/Glissando_20sl_monitor"  # Change this to your folder path
CHECK_INTERVAL = 30  # Check every 10 seconds
MAX_TMP_AGE = 6 * 60  # 6 minutes in seconds
NO_TMP_TIMEOUT = 5 * 60  # 5 minutes in seconds

# Tracking
tmp_file_times = {}
last_tmp_seen_time = None
scan_in_progress = False
active_scans = set()
completed_scans = set()

def get_tmp_files():
    return {os.path.splitext(f)[0] for f in os.listdir(FOLDER_TO_WATCH) if f.endswith('.tmp')}

def get_svs_files():
    return {os.path.splitext(f)[0] for f in os.listdir(FOLDER_TO_WATCH) if f.endswith('.svs')}  

def notify(title, message):
    print(f"[{datetime.now()}] {message}")
    notification.notify(
        title=title,
        message=message,
        app_name="WSI Monitor",
        timeout=10
    )

def main():
    global last_tmp_seen_time, scan_in_progress
    
    print("Starting Glissando 20SL Monitor...")
    
    while True:
        try:
            now = time.time()
            
            current_tmp_files = get_tmp_files()
            svs_files = get_svs_files()
            
            # Notify if idle and not already notified
            if not current_tmp_files and not scan_in_progress:
                notify("Device status - Idle", "No slides are being scanned.")
            
            # Check for new .tmp files
            if not scan_in_progress and current_tmp_files:
                scan_in_progress = True
                notified_idle = False
                notify("Scan Started", "WSI scanning has started.")
                
            # Track new .tmp files with timestamps
            for tmp_file in current_tmp_files:
                if tmp_file not in tmp_file_times:
                    tmp_file_times[tmp_file] = now
                    notify("Slide Scanning", f"Scanning started for slide: {tmp_file}.tmp")
                    
                    
                # Track active scans by basename without extension
                base_name = os.path.splitext(tmp_file)[0]
                if base_name not in active_scans and base_name not in completed_scans:
                    active_scans.add(base_name)
                    
            # Remove tmp files that disappeared (converted to .svs)
            tracked_tmp_files = list(tmp_file_times.keys())
            for tracked_tmp in tracked_tmp_files:
                if tracked_tmp not in current_tmp_files:
                    tmp_file_times.pop(tracked_tmp, None)
                    
            # Check for tmp files stuck longer than MAX_TMP_AGE
            for tmp_file, first_seen in list(tmp_file_times.items()):
                age = now - first_seen
                if age > MAX_TMP_AGE:
                    notify("Scan Error",
                           f"Slide '{tmp_file}' .tmp file exists for over {MAX_TMP_AGE // 60} minutes. Possible stall")
                    tmp_file_times.pop(tmp_file)
                    
            # Check completed scans (.svs files)
            for active_scan in list(active_scans):          
                if active_scan in svs_files:
                    notify("Slide WSI Saved", f"Slide Saved: {active_scan}.svs")
                    active_scans.remove(active_scan)
                    completed_scans.add(active_scan)
                    
            # Update last time we saw any .tmp files
            if current_tmp_files:
                last_tmp_seen_time = now
            
            # Check if scan run completed (no. tmp files for NO_TMP_TIMEOUT and scan was active)
            if scan_in_progress and last_tmp_seen_time and (now - last_tmp_seen_time) > NO_TMP_TIMEOUT:
                notify("Batch Scan Complete", f"All files scanned and device in idle state.")
                scan_in_progress = False
                active_scans.clear()
                completed_scans.clear()
                tmp_file_times.clear()
                
        except Exception as e:
            notify("Error", f"An error occurred: {e}")
            
        time.sleep(CHECK_INTERVAL)
        
if __name__ == "__main__":
    main()
            