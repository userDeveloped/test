import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
import threading
import numpy as np
import os
from datetime import datetime

class DarkCameraGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Multi-Camera Monitor")
        self.root.geometry("1200x800")
        self.root.configure(bg='#1e1e1e')
        
        # Variables
        self.cameras = []
        self.active_cameras = {}  # {camera_index: {'cap': cv2.VideoCapture, 'thread': thread, 'active': bool}}
        self.camera_labels = {}   # {camera_index: label_widget}
        self.recording = False
        self.video_writers = {}   # {camera_index: cv2.VideoWriter}
        self.recording_start_time = None
        
        # Configure dark theme
        self.configure_dark_theme()
        
        # Create GUI elements
        self.create_widgets()
        
        # Detect cameras on startup
        self.detect_cameras()
    
    def configure_dark_theme(self):
        """Configure dark theme for ttk widgets"""
        style = ttk.Style()
        
        # Use a theme that works well with customization
        try:
            style.theme_use('clam')
        except:
            style.theme_use('default')
        
        # Button styles
        style.configure('Start.TButton', 
                       background='#00aa44', 
                       foreground='white',
                       focuscolor='none')
        style.map('Start.TButton',
                 background=[('active', '#00cc55')])
        
        style.configure('Stop.TButton', 
                       background='#cc3333', 
                       foreground='white',
                       focuscolor='none')
        style.map('Stop.TButton',
                 background=[('active', '#dd4444')])
        
        style.configure('Custom.TButton', 
                       background='#404040', 
                       foreground='white',
                       focuscolor='none')
        style.map('Custom.TButton',
                 background=[('active', '#505050')])
    
    def create_widgets(self):
        # Main container
        main_frame = tk.Frame(self.root, bg='#1e1e1e')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top section - Camera detection and controls
        top_frame = tk.Frame(main_frame, bg='#1e1e1e')
        top_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Left side - Camera detection
        detection_frame = tk.LabelFrame(top_frame, text="🎥 Detected Cameras", 
                                      bg='#1e1e1e', fg='#00ff88', 
                                      font=('Arial', 10, 'bold'))
        detection_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Camera list with dark styling
        list_frame = tk.Frame(detection_frame, bg='#1e1e1e')
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.camera_listbox = tk.Listbox(list_frame, 
                                       bg='#2d2d2d', 
                                       fg='#ffffff',
                                       selectbackground='#00aa44',
                                       selectforeground='white',
                                       font=('Consolas', 10),
                                       borderwidth=0,
                                       highlightthickness=0)
        self.camera_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame, bg='#404040', troughcolor='#2d2d2d')
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.camera_listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.configure(command=self.camera_listbox.yview)
        
        # Right side - Controls
        control_frame = tk.LabelFrame(top_frame, text="🎛️ Controls", 
                                    bg='#1e1e1e', fg='#00ff88',
                                    font=('Arial', 10, 'bold'))
        control_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        # Refresh button
        refresh_btn = ttk.Button(control_frame, text="🔄 Refresh Cameras", 
                               command=self.detect_cameras, style='Custom.TButton')
        refresh_btn.pack(pady=10, padx=15, fill=tk.X)
        
        # Global controls
        tk.Label(control_frame, text="Global Controls:", 
               bg='#1e1e1e', fg='#ffffff', 
               font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(10, 5), padx=15)
        
        start_all_btn = ttk.Button(control_frame, text="🔴 Start Recording All", 
                                 command=self.start_recording_all, style='Start.TButton')
        start_all_btn.pack(pady=2, padx=15, fill=tk.X)
        
        stop_all_btn = ttk.Button(control_frame, text="⏹️ Stop Recording All", 
                                command=self.stop_recording_all, style='Stop.TButton')
        stop_all_btn.pack(pady=2, padx=15, fill=tk.X)
        
        # Individual camera controls
        tk.Label(control_frame, text="Individual Controls:", 
               bg='#1e1e1e', fg='#ffffff',
               font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(15, 5), padx=15)
        
        self.individual_frame = tk.Frame(control_frame, bg='#1e1e1e')
        self.individual_frame.pack(fill=tk.BOTH, expand=True, padx=15)
        
        # Camera grid section
        grid_frame = tk.LabelFrame(main_frame, text="📹 Camera Feeds", 
                                 bg='#1e1e1e', fg='#00ff88',
                                 font=('Arial', 10, 'bold'))
        grid_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create camera grid container
        self.camera_grid = tk.Frame(grid_frame, bg='#1e1e1e')
        self.camera_grid.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Status bar
        status_frame = tk.Frame(main_frame, bg='#1e1e1e', height=30)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        status_frame.pack_propagate(False)
        
        self.status_var = tk.StringVar()
        self.status_var.set("🔍 Ready - Click 'Refresh Cameras' to detect cameras")
        status_label = tk.Label(status_frame, textvariable=self.status_var,
                              bg='#2d2d2d', fg='#00ff88', 
                              font=('Arial', 9), anchor=tk.W, padx=10)
        status_label.pack(fill=tk.BOTH, expand=True)
    
    def detect_cameras(self):
        """Detect available cameras and populate the GUI"""
        self.cameras = []
        self.camera_listbox.delete(0, tk.END)
        
        self.status_var.set("🔍 Detecting cameras...")
        self.root.update()
        
        # More robust camera detection for Linux
        import os
        import glob
        
        # First, check /dev/video* devices (Linux specific)
        video_devices = []
        if os.name == 'posix':  # Linux/Unix
            video_devices = sorted([int(d.split('video')[1]) for d in glob.glob('/dev/video*') 
                                  if d.split('video')[1].isdigit()])
        
        # If no video devices found, fall back to testing indices 0-5
        if not video_devices:
            video_devices = list(range(6))
        
        # Test each potential camera index
        for i in video_devices:
            try:
                # Use a more careful approach to avoid segfaults
                cap = None
                try:
                    # Set backend explicitly to avoid issues
                    cap = cv2.VideoCapture(i, cv2.CAP_V4L2)  # Use V4L2 backend on Linux
                    
                    # Give it time to initialize
                    import time
                    time.sleep(0.1)
                    
                    # Test if camera actually works by trying to read a frame
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            # Get camera properties
                            width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                            height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                            fps = cap.get(cv2.CAP_PROP_FPS)
                            
                            camera_info = {
                                'index': i,
                                'width': int(width) if width > 0 else 640,
                                'height': int(height) if height > 0 else 480,
                                'fps': int(fps) if fps > 0 else 30
                            }
                            
                            self.cameras.append(camera_info)
                            
                            # Add to listbox with nice formatting
                            info_text = f"📷 Camera {i:2d} │ {int(width):4d}×{int(height):4d} │ {fps if fps > 0 else 'N/A':>3} FPS"
                            self.camera_listbox.insert(tk.END, info_text)
                            
                            print(f"Found working camera at index {i}")
                        else:
                            print(f"Camera {i} opened but couldn't read frame")
                    else:
                        print(f"Camera {i} failed to open")
                        
                except Exception as e:
                    print(f"Error testing camera {i}: {e}")
                    
                finally:
                    # Always release the camera
                    if cap is not None:
                        try:
                            cap.release()
                        except:
                            pass
                        
            except Exception as e:
                print(f"Critical error with camera {i}: {e}")
                continue
        
        if self.cameras:
            self.status_var.set(f"✅ Found {len(self.cameras)} working camera(s)")
            self.create_individual_controls()
            self.setup_camera_grid()
        else:
            self.status_var.set("❌ No working cameras detected")
            messagebox.showwarning("No Cameras", 
                                 "No working cameras were detected.\n\n" +
                                 "Make sure your cameras are:\n" +
                                 "• Properly connected\n" +
                                 "• Not being used by other applications\n" +
                                 "• Have proper permissions (/dev/video* readable)")
    
    def create_individual_controls(self):
        """Create individual start/stop buttons for each camera"""
        # Clear existing controls
        for widget in self.individual_frame.winfo_children():
            widget.destroy()
        
        for cam in self.cameras:
            cam_frame = tk.Frame(self.individual_frame, bg='#1e1e1e')
            cam_frame.pack(fill=tk.X, pady=2)
            
            # Camera label
            cam_label = tk.Label(cam_frame, text=f"Camera {cam['index']}:", 
                               bg='#1e1e1e', fg='#ffffff', width=10)
            cam_label.pack(side=tk.LEFT)
            
            # Start button
            start_btn = ttk.Button(cam_frame, text="▶", width=3,
                                 command=lambda idx=cam['index']: self.start_camera(idx),
                                 style='Start.TButton')
            start_btn.pack(side=tk.LEFT, padx=(5, 2))
            
            # Stop button  
            stop_btn = ttk.Button(cam_frame, text="⏹", width=3,
                                command=lambda idx=cam['index']: self.stop_camera(idx),
                                style='Stop.TButton')
            stop_btn.pack(side=tk.LEFT, padx=2)
    
    def setup_camera_grid(self):
        """Setup the camera display grid"""
        # Clear existing camera displays
        for widget in self.camera_grid.winfo_children():
            widget.destroy()
        self.camera_labels = {}
        
        num_cameras = len(self.cameras)
        if num_cameras == 0:
            return
        
        # Always arrange cameras horizontally in a single row
        rows = 1
        cols = num_cameras
        
        # Configure grid weights for horizontal layout
        self.camera_grid.rowconfigure(0, weight=1)  # Single row takes full height
        for j in range(cols):
            self.camera_grid.columnconfigure(j, weight=1)  # Each column gets equal width
        
        # Create camera display slots horizontally
        for idx, cam in enumerate(self.cameras):
            row = 0  # Always first row
            col = idx  # Column equals camera index
            
            # Camera frame
            cam_frame = tk.Frame(self.camera_grid, bg='#2d2d2d', relief=tk.RAISED, bd=2)
            cam_frame.grid(row=row, column=col, padx=5, pady=5, sticky='nsew')
            
            # Camera title
            title_label = tk.Label(cam_frame, text=f"📷 Camera {cam['index']}", 
                                 bg='#2d2d2d', fg='#00ff88', 
                                 font=('Arial', 12, 'bold'))
            title_label.pack(pady=5)
            
            # Video display area - make it fill the available space
            video_label = tk.Label(cam_frame, text="Camera Offline", 
                                 bg='#1a1a1a', fg='#666666',
                                 font=('Arial', 14))
            video_label.pack(expand=True, fill=tk.BOTH, padx=5, pady=(0, 5))
            
            self.camera_labels[cam['index']] = video_label
    
    def start_camera(self, camera_index):
        """Start a specific camera"""
        if camera_index in self.active_cameras and self.active_cameras[camera_index]['active']:
            return  # Already running
        
        try:
            # Use V4L2 backend explicitly on Linux for better compatibility
            if os.name == 'posix':
                cap = cv2.VideoCapture(camera_index, cv2.CAP_V4L2)
            else:
                cap = cv2.VideoCapture(camera_index)
                
            if not cap.isOpened():
                raise Exception(f"Failed to open camera {camera_index}")
            
            # Test that we can actually read frames
            ret, frame = cap.read()
            if not ret or frame is None:
                cap.release()
                raise Exception(f"Camera {camera_index} opened but cannot read frames")
            
            self.active_cameras[camera_index] = {
                'cap': cap,
                'active': True,
                'thread': None
            }
            
            # Start video thread
            thread = threading.Thread(target=self.update_camera_feed, 
                                    args=(camera_index,), daemon=True)
            thread.start()
            self.active_cameras[camera_index]['thread'] = thread
            
            self.status_var.set(f"▶️ Camera {camera_index} started")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start camera {camera_index}: {str(e)}")
            print(f"Camera {camera_index} start error: {e}")
    
    def stop_camera(self, camera_index):
        """Stop a specific camera"""
        if camera_index not in self.active_cameras:
            return
        
        self.active_cameras[camera_index]['active'] = False
        
        if self.active_cameras[camera_index]['cap']:
            self.active_cameras[camera_index]['cap'].release()
        
        # Clear display
        if camera_index in self.camera_labels:
            self.camera_labels[camera_index].configure(image="", text="Camera Offline")
        
        del self.active_cameras[camera_index]
        self.status_var.set(f"⏹️ Camera {camera_index} stopped")
    
    def start_recording_all(self):
        """Start recording with all available cameras"""
        if self.recording:
            messagebox.showwarning("Already Recording", "Recording is already in progress!")
            return
            
        if not self.cameras:
            messagebox.showerror("No Cameras", "No cameras detected. Please refresh cameras first.")
            return
        
        # Ask user where to save recordings
        save_directory = filedialog.askdirectory(
            title="Select Directory to Save Recordings",
            initialdir=os.path.expanduser("~/Desktop")
        )
        
        if not save_directory:
            return  # User cancelled
        
        self.recording = True
        self.recording_start_time = datetime.now()
        self.video_writers = {}
        
        # Start all cameras and set up recording
        for cam in self.cameras:
            camera_index = cam['index']
            
            try:
                # Start camera if not already active
                if camera_index not in self.active_cameras or not self.active_cameras[camera_index]['active']:
                    self.start_camera(camera_index)
                
                # Wait a moment for camera to initialize
                self.root.after(500)
                
                # Set up video writer
                timestamp = self.recording_start_time.strftime("%Y%m%d_%H%M%S")
                filename = f"camera_{camera_index}_{timestamp}.avi"
                filepath = os.path.join(save_directory, filename)
                
                # Get camera properties
                cap = self.active_cameras[camera_index]['cap']
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = int(cap.get(cv2.CAP_PROP_FPS)) if cap.get(cv2.CAP_PROP_FPS) > 0 else 20
                
                # Create video writer
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
                writer = cv2.VideoWriter(filepath, fourcc, fps, (width, height))
                
                if writer.isOpened():
                    self.video_writers[camera_index] = {
                        'writer': writer,
                        'filepath': filepath,
                        'frames_written': 0,
                        'last_write_time': 0,
                        'frame_interval': 1.0 / fps  # Time between frames
                    }
                else:
                    raise Exception(f"Failed to create video writer for camera {camera_index}")
                    
            except Exception as e:
                messagebox.showerror("Recording Error", f"Failed to start recording for camera {camera_index}: {str(e)}")
                self.stop_recording_all()
                return
        
        self.status_var.set(f"🔴 Recording {len(self.video_writers)} cameras to: {os.path.basename(save_directory)}")
        messagebox.showinfo("Recording Started", 
                           f"Recording started for {len(self.video_writers)} cameras.\n"
                           f"Saving to: {save_directory}")
    
    def stop_recording_all(self):
        """Stop recording all cameras and save files"""
        if not self.recording:
            messagebox.showwarning("Not Recording", "No recording in progress!")
            return
        
        self.recording = False
        recording_duration = datetime.now() - self.recording_start_time if self.recording_start_time else None
        
        # Close all video writers and collect info
        saved_files = []
        for camera_index, writer_info in self.video_writers.items():
            try:
                writer_info['writer'].release()
                
                # Check if file was actually created and has content
                if os.path.exists(writer_info['filepath']) and os.path.getsize(writer_info['filepath']) > 1024:
                    saved_files.append({
                        'camera': camera_index,
                        'filepath': writer_info['filepath'],
                        'frames': writer_info['frames_written']
                    })
                else:
                    # Remove empty or invalid files
                    if os.path.exists(writer_info['filepath']):
                        os.remove(writer_info['filepath'])
                    
            except Exception as e:
                print(f"Error closing video writer for camera {camera_index}: {e}")
        
        self.video_writers = {}
        
        # Show summary dialog
        if saved_files:
            duration_str = ""
            if recording_duration:
                total_seconds = int(recording_duration.total_seconds())
                minutes, seconds = divmod(total_seconds, 60)
                duration_str = f"Duration: {minutes}m {seconds}s\n"
            
            file_list = "\n".join([f"• Camera {info['camera']}: {os.path.basename(info['filepath'])} ({info['frames']} frames)" 
                                  for info in saved_files])
            
            message = f"Recording stopped successfully!\n\n{duration_str}Files saved:\n{file_list}\n\nLocation: {os.path.dirname(saved_files[0]['filepath'])}"
            messagebox.showinfo("Recording Complete", message)
            
            # Ask if user wants to open the folder
            if messagebox.askyesno("Open Folder", "Would you like to open the folder containing the recordings?"):
                try:
                    import subprocess
                    import platform
                    folder_path = os.path.dirname(saved_files[0]['filepath'])
                    
                    if platform.system() == "Windows":
                        os.startfile(folder_path)
                    elif platform.system() == "Darwin":  # macOS
                        subprocess.run(["open", folder_path])
                    else:  # Linux
                        subprocess.run(["xdg-open", folder_path])
                except Exception as e:
                    print(f"Could not open folder: {e}")
        else:
            messagebox.showerror("Recording Failed", "No video files were successfully created.")
        
        self.status_var.set("⏹️ Recording stopped")
    
    def start_all_cameras(self):
        """Start all available cameras (without recording)"""
        for cam in self.cameras:
            self.start_camera(cam['index'])
        self.status_var.set("▶️ All cameras started")
    
    def stop_all_cameras(self):
        """Stop all active cameras"""
        # Stop recording if active
        if self.recording:
            self.stop_recording_all()
            
        camera_indices = list(self.active_cameras.keys())
        for camera_index in camera_indices:
            self.stop_camera(camera_index)
        self.status_var.set("⏹️ All cameras stopped")
    
    def update_camera_feed(self, camera_index):
        """Update video feed for a specific camera"""
        cap = self.active_cameras[camera_index]['cap']
        
        while (camera_index in self.active_cameras and 
               self.active_cameras[camera_index]['active']):
            
            ret, frame = cap.read()
            if ret:
                current_time = threading.current_thread().ident
                
                # Write frame to video file if recording (with timing control)
                if self.recording and camera_index in self.video_writers:
                    try:
                        writer_info = self.video_writers[camera_index]
                        current_timestamp = cv2.getTickCount() / cv2.getTickFrequency()
                        
                        # Only write frame if enough time has passed (frame rate limiting)
                        if (current_timestamp - writer_info['last_write_time']) >= writer_info['frame_interval']:
                            writer_info['writer'].write(frame)
                            writer_info['frames_written'] += 1
                            writer_info['last_write_time'] = current_timestamp
                            
                            # Optional: Add slight delay to prevent overwhelming the writer
                            if writer_info['frames_written'] % 30 == 0:  # Every 30 frames
                                threading.Event().wait(0.01)  # 10ms pause
                                
                    except Exception as e:
                        print(f"Error writing frame for camera {camera_index}: {e}")
                
                # Update display frame in main thread to get current widget size
                self.root.after(0, self.update_display_frame, camera_index, frame.copy())
                    
                # Small delay to prevent overwhelming the system
                threading.Event().wait(0.033)  # ~30 FPS limit for display
                    
            else:
                # Handle camera error
                self.root.after(0, self.handle_camera_error, camera_index)
                break
    
    def update_display_frame(self, camera_index, frame):
        """Update display frame with current widget dimensions"""
        if camera_index not in self.camera_labels:
            return
            
        label_widget = self.camera_labels[camera_index]
        
        try:
            # Force update to get current dimensions
            label_widget.update_idletasks()
            widget_width = label_widget.winfo_width()
            widget_height = label_widget.winfo_height()
            
            # Skip if widget is too small or not properly initialized
            if widget_width <= 10 or widget_height <= 10:
                return
                
            # Calculate aspect ratio to maintain proportions
            original_height, original_width = frame.shape[:2]
            aspect_ratio = original_width / original_height
            
            # Calculate new dimensions while maintaining aspect ratio
            if widget_width / widget_height > aspect_ratio:
                # Window is wider than video aspect ratio
                new_height = widget_height
                new_width = int(widget_height * aspect_ratio)
            else:
                # Window is taller than video aspect ratio
                new_width = widget_width
                new_height = int(widget_width / aspect_ratio)
            
            # Ensure minimum size
            new_width = max(new_width, 100)
            new_height = max(new_height, 75)
            
            # Resize frame to calculated dimensions
            display_frame = cv2.resize(frame, (new_width, new_height))
            
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            
            # Convert to tkinter PhotoImage
            height, width, channels = frame_rgb.shape
            ppm_header = f'P6\n{width} {height}\n255\n'.encode()
            ppm_data = ppm_header + frame_rgb.tobytes()
            photo = tk.PhotoImage(data=ppm_data, format='PPM')
            
            # Update label
            self.update_camera_label(camera_index, photo)
            
        except Exception as e:
            print(f"Error updating display for camera {camera_index}: {e}")
    
    def update_camera_label(self, camera_index, photo):
        """Update camera label with new frame"""
        if camera_index in self.camera_labels:
            # Add recording indicator if recording
            if self.recording and camera_index in self.video_writers:
                # You could add a red dot or text overlay here if desired
                pass
            
            self.camera_labels[camera_index].configure(image=photo, text="")
            self.camera_labels[camera_index].image = photo  # Keep reference
    
    def handle_camera_error(self, camera_index):
        """Handle camera errors"""
        self.stop_camera(camera_index)
        messagebox.showerror("Camera Error", f"Lost connection to camera {camera_index}")
    
    def on_closing(self):
        """Handle window closing"""
        if self.recording:
            self.stop_recording_all()
        self.stop_all_cameras()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = DarkCameraGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()