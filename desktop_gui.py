#!/usr/bin/env python3
"""
DocScan Desktop GUI - Tkinter-based real-time document enhancer
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
from pathlib import Path
import json
import threading
import zipfile
import shutil

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False

try:
    import pymupdf as fitz
    HAS_PYMUPDF = True
except ImportError:
    try:
        import fitz
        HAS_PYMUPDF = True
    except ImportError:
        HAS_PYMUPDF = False


class DocScanGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("DocScan - Document Enhancer")
        self.root.geometry("1400x800")
        
        # Variables
        self.image_path = None
        self.original_img = None
        self.gray_img = None
        self.batch_files = []
        self.batch_file_objects = []  # For storing metadata like pdf pages
        self.is_processing = False
        self.show_comparison = False
        self.current_pdf_doc = None
        self.current_pdf_page = 0
        
        # Default settings
        self.settings = {
            "kernel_divisor": 8,
            "gamma": 0.7,
            "use_clahe": False,
            "clahe_clip": 2.5,
            "use_sharpen": False,
            "sharpen_amount": 1.0,
            "use_denoise": False,
            "denoise_strength": 3,
            "pdf_dpi": 300
        }
        
        # Load saved settings if they exist
        self.load_settings()
        
        # Create GUI
        self.create_gui()
        
        # Setup drag-and-drop
        if HAS_DND:
            self.setup_drag_and_drop()
    
    def create_gui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Left panel - Controls
        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding="10")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.N), padx=(0, 10))
        
        # === Single Image Section ===
        ttk.Label(control_frame, text="Single Image", font=('', 10, 'bold')).grid(
            row=0, column=0, columnspan=3, pady=(0, 5), sticky=tk.W
        )
        ttk.Button(control_frame, text="Open Image", command=self.open_image).grid(
            row=1, column=0, columnspan=3, pady=(0, 5), sticky=(tk.W, tk.E)
        )
        
        # Comparison toggle
        self.comparison_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(control_frame, text="Show Before/After", variable=self.comparison_var,
                        command=self.toggle_comparison).grid(row=2, column=0, columnspan=3, sticky=tk.W)
        
        # === Batch Processing Section ===
        ttk.Separator(control_frame, orient='horizontal').grid(
            row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5
        )
        ttk.Label(control_frame, text="Batch Processing", font=('', 10, 'bold')).grid(
            row=4, column=0, columnspan=3, pady=(0, 5), sticky=tk.W
        )
        ttk.Button(control_frame, text="Select Multiple Files", command=self.select_batch_files).grid(
            row=5, column=0, columnspan=3, pady=(0, 5), sticky=(tk.W, tk.E)
        )
        ttk.Button(control_frame, text="Select Folder", command=self.select_batch_folder).grid(
            row=6, column=0, columnspan=3, pady=(0, 10), sticky=(tk.W, tk.E)
        )
        
        # Batch status
        self.batch_status_var = tk.StringVar(value="No files selected")
        ttk.Label(control_frame, textvariable=self.batch_status_var, wraplength=200).grid(
            row=7, column=0, columnspan=3, pady=(0, 5), sticky=tk.W
        )
        
        # === Parameters Section ===
        ttk.Separator(control_frame, orient='horizontal').grid(
            row=8, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5
        )
        ttk.Label(control_frame, text="Parameters", font=('', 10, 'bold')).grid(
            row=9, column=0, columnspan=3, pady=(0, 5), sticky=tk.W
        )
        
        # Kernel Divisor
        ttk.Label(control_frame, text="Kernel Divisor:").grid(row=10, column=0, sticky=tk.W)
        self.kernel_var = tk.IntVar(value=self.settings["kernel_divisor"])
        self.kernel_scale = ttk.Scale(
            control_frame, from_=4, to=20, variable=self.kernel_var,
            orient=tk.HORIZONTAL, command=lambda x: self.on_slider_change()
        )
        self.kernel_scale.grid(row=10, column=1, sticky=(tk.W, tk.E), padx=(5, 5))
        self.kernel_entry = ttk.Entry(control_frame, textvariable=self.kernel_var, width=6)
        self.kernel_entry.grid(row=10, column=2)
        self.kernel_entry.bind('<Return>', lambda e: self.on_entry_change("kernel"))
        self.kernel_entry.bind('<FocusOut>', lambda e: self.on_entry_change("kernel"))
        
        # Gamma
        ttk.Label(control_frame, text="Gamma:").grid(row=11, column=0, sticky=tk.W)
        self.gamma_var = tk.DoubleVar(value=self.settings["gamma"])
        self.gamma_scale = ttk.Scale(
            control_frame, from_=0.3, to=1.5, variable=self.gamma_var,
            orient=tk.HORIZONTAL, command=lambda x: self.on_slider_change()
        )
        self.gamma_scale.grid(row=11, column=1, sticky=(tk.W, tk.E), padx=(5, 5))
        self.gamma_entry = ttk.Entry(control_frame, textvariable=self.gamma_var, width=6)
        self.gamma_entry.grid(row=11, column=2)
        self.gamma_entry.bind('<Return>', lambda e: self.on_entry_change("gamma"))
        self.gamma_entry.bind('<FocusOut>', lambda e: self.on_entry_change("gamma"))
        
        # CLAHE Checkbox
        self.clahe_var = tk.BooleanVar(value=self.settings["use_clahe"])
        ttk.Checkbutton(control_frame, text="Apply CLAHE", variable=self.clahe_var,
                        command=self.update_preview).grid(row=12, column=0, columnspan=3, sticky=tk.W)
        
        # CLAHE Clip
        ttk.Label(control_frame, text="CLAHE Clip:").grid(row=13, column=0, sticky=tk.W)
        self.clahe_clip_var = tk.DoubleVar(value=self.settings["clahe_clip"])
        self.clahe_clip_scale = ttk.Scale(
            control_frame, from_=1.0, to=5.0, variable=self.clahe_clip_var,
            orient=tk.HORIZONTAL, command=lambda x: self.on_slider_change()
        )
        self.clahe_clip_scale.grid(row=13, column=1, sticky=(tk.W, tk.E), padx=(5, 5))
        self.clahe_clip_entry = ttk.Entry(control_frame, textvariable=self.clahe_clip_var, width=6)
        self.clahe_clip_entry.grid(row=13, column=2)
        self.clahe_clip_entry.bind('<Return>', lambda e: self.on_entry_change("clahe_clip"))
        self.clahe_clip_entry.bind('<FocusOut>', lambda e: self.on_entry_change("clahe_clip"))
        
        # Sharpen Checkbox
        self.sharpen_var = tk.BooleanVar(value=self.settings["use_sharpen"])
        ttk.Checkbutton(control_frame, text="Apply Sharpening", variable=self.sharpen_var,
                        command=self.update_preview).grid(row=14, column=0, columnspan=3, sticky=tk.W)
        
        # Denoise Checkbox
        self.denoise_var = tk.BooleanVar(value=self.settings["use_denoise"])
        ttk.Checkbutton(control_frame, text="Apply Denoising", variable=self.denoise_var,
                        command=self.update_preview).grid(row=15, column=0, columnspan=3, sticky=tk.W)
        
        # === DPI Setting ===
        ttk.Separator(control_frame, orient='horizontal').grid(
            row=16, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5
        )
        ttk.Label(control_frame, text="PDF DPI:", font=('', 10, 'bold')).grid(
            row=17, column=0, sticky=tk.W
        )
        self.dpi_var = tk.StringVar(value=str(self.settings["pdf_dpi"]))
        dpi_combo = ttk.Combobox(
            control_frame, textvariable=self.dpi_var,
            values=["72", "150", "300", "600"], state="readonly", width=8
        )
        dpi_combo.grid(row=17, column=1, columnspan=2, sticky=(tk.W, tk.E))
        
        # === Buttons Section ===
        ttk.Separator(control_frame, orient='horizontal').grid(
            row=18, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5
        )
        
        # Save buttons
        ttk.Button(control_frame, text="Save Settings", command=self.save_settings).grid(
            row=19, column=0, pady=(5, 5), sticky=(tk.W, tk.E)
        )
        ttk.Button(control_frame, text="Save Image", command=self.save_image).grid(
            row=19, column=2, pady=(5, 5), sticky=(tk.W, tk.E)
        )
        
        # Batch process button
        self.batch_btn = ttk.Button(
            control_frame, text="Process Batch", 
            command=self.process_batch, state=tk.DISABLED
        )
        self.batch_btn.grid(row=20, column=0, columnspan=3, pady=(5, 0), sticky=(tk.W, tk.E))
        
        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            control_frame, variable=self.progress_var, 
            maximum=100, mode='determinate'
        )
        self.progress_bar.grid(row=21, column=0, columnspan=3, pady=(5, 0), sticky=(tk.W, tk.E))
        
        # Configure column weights
        control_frame.columnconfigure(1, weight=1)
        
        # Right panel - Image display
        image_frame = ttk.LabelFrame(main_frame, text="Preview", padding="10")
        image_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Single view
        self.single_frame = ttk.Frame(image_frame)
        self.single_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.image_label = ttk.Label(self.single_frame, text="No image loaded")
        self.image_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Comparison view
        self.comparison_frame = ttk.Frame(image_frame)
        self.comparison_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.comparison_frame.grid_remove()  # Hidden by default
        
        self.original_label = ttk.Label(self.comparison_frame, text="Original")
        self.original_label.grid(row=0, column=0, padx=(0, 5), sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.processed_label = ttk.Label(self.comparison_frame, text="Processed")
        self.processed_label.grid(row=0, column=1, padx=(5, 0), sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        image_frame.columnconfigure(0, weight=1)
        image_frame.rowconfigure(0, weight=1)
        self.single_frame.columnconfigure(0, weight=1)
        self.single_frame.rowconfigure(0, weight=1)
        self.comparison_frame.columnconfigure(0, weight=1)
        self.comparison_frame.columnconfigure(1, weight=1)
        self.comparison_frame.rowconfigure(0, weight=1)
    
    def setup_drag_and_drop(self):
        """Setup drag-and-drop for image files"""
        try:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self.on_drop)
        except Exception as e:
            print(f"Drag-and-drop setup failed: {e}")
    
    def on_drop(self, event):
        """Handle dropped files"""
        files = self.root.tk.splitlist(event.data)
        if files:
            file_path = files[0]
            if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff')):
                self.load_image(file_path)
    
    def on_slider_change(self):
        """Called when a slider is moved"""
        self.update_preview()
    
    def on_entry_change(self, param):
        """Called when entry is edited - validates and updates slider"""
        try:
            if param == "kernel":
                value = int(self.kernel_var.get())
                value = max(4, min(20, value))
                self.kernel_var.set(value)
            elif param == "gamma":
                value = float(self.gamma_var.get())
                value = max(0.3, min(1.5, value))
                self.gamma_var.set(round(value, 2))
            elif param == "clahe_clip":
                value = float(self.clahe_clip_var.get())
                value = max(1.0, min(5.0, value))
                self.clahe_clip_var.set(round(value, 1))
        except (ValueError, tk.TclError):
            pass
        
        self.update_preview()
    
    def toggle_comparison(self):
        """Toggle between single and comparison view"""
        self.show_comparison = self.comparison_var.get()
        
        if self.show_comparison:
            self.single_frame.grid_remove()
            self.comparison_frame.grid()
        else:
            self.comparison_frame.grid_remove()
            self.single_frame.grid()
        
        self.update_preview()
    
    def open_image(self):
        filetypes = [
            ("All files", "*.*"),
            ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff")
        ]
        if HAS_PYMUPDF:
            filetypes.insert(0, ("PDF files", "*.pdf"))
        
        file_path = filedialog.askopenfilename(
            filetypes=filetypes
        )
        
        if file_path:
            self.load_image(file_path)
    
    def load_image(self, file_path):
        """Load an image from file path"""
        self.image_path = Path(file_path)
        self.current_pdf_doc = None
        self.current_pdf_page = 0
        
        if file_path.lower().endswith('.pdf') and HAS_PYMUPDF:
            try:
                doc = fitz.open(file_path)
                if not doc.is_pdf:
                    doc.close()
                    # Not a PDF, treat as image
                    self.original_img = cv2.imread(file_path)
                    if self.original_img is not None:
                        self.gray_img = cv2.cvtColor(self.original_img, cv2.COLOR_BGR2GRAY)
                        self.update_preview()
                    return
                # Load first page of PDF
                if len(doc) == 0:
                    doc.close()
                    messagebox.showerror("Error", "Empty PDF file")
                    return
                page = doc[0]
                self.current_pdf_doc = doc
                self.current_pdf_page = 0
                dpi = max(200, min(600, int(self.dpi_var.get())))
                pix = page.get_pixmap(dpi=dpi)
                self.original_img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)
                if pix.n == 4:
                    self.original_img = cv2.cvtColor(self.original_img, cv2.COLOR_BGRA2BGR)
                else:
                    self.original_img = cv2.cvtColor(self.original_img, cv2.COLOR_RGB2BGR)
                if self.original_img is not None:
                    self.gray_img = cv2.cvtColor(self.original_img, cv2.COLOR_BGR2GRAY)
                    self.update_preview()
                return
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load PDF: {e}")
                return
        else:
            # Regular image file
            self.original_img = cv2.imread(file_path)
            if self.original_img is not None:
                self.gray_img = cv2.cvtColor(self.original_img, cv2.COLOR_BGR2GRAY)
                self.update_preview()
            else:
                messagebox.showerror("Error", "Could not load image")

    def select_batch_files(self):
        """Select multiple image files for batch processing"""
        filetypes = [
            ("All files", "*.*"),
            ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff")
        ]
        if HAS_PYMUPDF:
            filetypes.insert(0, ("PDF files", "*.pdf"))
            filetypes.insert(0, ("Supported files", "*.pdf *.jpg *.jpeg *.png *.bmp *.tiff"))
        
        file_paths = filedialog.askopenfilenames(
            title="Select Images",
            filetypes=filetypes
        )
        
        if file_paths:
            self.batch_files = [Path(f) for f in file_paths]
            self.batch_status_var.set(f"{len(self.batch_files)} files selected")
            self.batch_btn.config(state=tk.NORMAL)
    
    def load_images_from_path(self, file_path, dpi=300):
        """Load all images from a file path (handles PDFs with multiple pages). Returns list of (name, cv2_img)."""
        results = []
        path = Path(file_path)
        if path.suffix.lower() == '.pdf' and HAS_PYMUPDF:
            try:
                doc = fitz.open(str(path))
                if not doc.is_pdf:
                    doc.close()
                    return results
                for i in range(len(doc)):
                    page = doc[i]
                    pix = page.get_pixmap(dpi=dpi)
                    img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)
                    if pix.n == 4:
                        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    else:
                        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                    results.append((f'{path.stem}_p{i+1}', img))
                doc.close()
            except Exception:
                pass
            return results
        else:
            try:
                img = cv2.imread(str(path))
                if img is not None:
                    results.append((path.stem, img))
            except Exception:
                pass
            return results


    def select_batch_folder(self):
        """Select a folder for batch processing"""
        folder_path = filedialog.askdirectory(title="Select Folder with Images")
        
        if folder_path:
            folder = Path(folder_path)
            if HAS_PYMUPDF:
                exts = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.pdf'}
            else:
                exts = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
            self.batch_files = [
                f for f in folder.iterdir() 
                if f.suffix.lower() in exts and f.is_file()
            ]
            self.batch_files.sort()
            
            if self.batch_files:
                self.batch_status_var.set(f"{len(self.batch_files)} files found")
                self.batch_btn.config(state=tk.NORMAL)
            else:
                messagebox.showwarning("No Images", "No image files found in the selected folder.")
                self.batch_files = []
                self.batch_status_var.set("No files selected")
                self.batch_btn.config(state=tk.DISABLED)
    
    def process_image(self, gray):
        """Process a single image with current settings"""
        # Get parameters
        kernel_divisor = int(self.kernel_var.get())
        gamma = self.gamma_var.get()
        use_clahe = self.clahe_var.get()
        clahe_clip = self.clahe_clip_var.get()
        use_sharpen = self.sharpen_var.get()
        use_denoise = self.denoise_var.get()
        
        # Step 1: Background normalization
        kernel_size = max(51, min(gray.shape) // kernel_divisor)
        kernel_size = min(kernel_size, 255)
        if kernel_size % 2 == 0:
            kernel_size += 1
        background = cv2.medianBlur(gray, kernel_size)
        bg_float = np.clip(background.astype(np.float32), 1, 255)
        normalized = (gray.astype(np.float32) / bg_float) * 255.0
        normalized = np.clip(normalized, 0, 255).astype(np.uint8)
        
        # Step 2: Optional CLAHE
        if use_clahe:
            clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=(8, 8))
            normalized = clahe.apply(normalized)
        
        # Step 3: Optional denoising
        if use_denoise:
            normalized = cv2.fastNlMeansDenoising(
                normalized, None, h=3, 
                templateWindowSize=7, searchWindowSize=21
            )
        
        # Step 4: Optional sharpening
        if use_sharpen:
            kernel = np.array([[-1,-1,-1],[-1,9,-1],[-1,-1,-1]])
            normalized = cv2.filter2D(normalized, -1, kernel)
        
        # Step 5: Gamma correction
        img_float = normalized.astype(np.float32) / 255.0
        img_float = np.power(img_float, gamma) * 255.0
        result = np.clip(img_float, 0, 255).astype(np.uint8)
        
        return result
    
    def update_preview(self):
        """Update the preview image"""
        if self.gray_img is None:
            return
        
        # Process image
        result = self.process_image(self.gray_img)
        
        if self.show_comparison:
            # Side-by-side comparison
            display_size = (400, 400)
            
            # Original
            orig_pil = Image.fromarray(self.gray_img)
            orig_pil.thumbnail(display_size, Image.Resampling.LANCZOS)
            self.orig_photo = ImageTk.PhotoImage(orig_pil)
            self.original_label.configure(image=self.orig_photo, text="")
            
            # Processed
            proc_pil = Image.fromarray(result)
            proc_pil.thumbnail(display_size, Image.Resampling.LANCZOS)
            self.proc_photo = ImageTk.PhotoImage(proc_pil)
            self.processed_label.configure(image=self.proc_photo, text="")
        else:
            # Single view
            pil_image = Image.fromarray(result)
            display_size = (600, 600)
            pil_image.thumbnail(display_size, Image.Resampling.LANCZOS)
            
            self.photo = ImageTk.PhotoImage(pil_image)
            self.image_label.configure(image=self.photo, text="")
    
    def save_settings(self):
        """Save current settings to JSON file"""
        settings = {
            "kernel_divisor": int(self.kernel_var.get()),
            "gamma": self.gamma_var.get(),
            "use_clahe": self.clahe_var.get(),
            "clahe_clip": self.clahe_clip_var.get(),
            "use_sharpen": self.sharpen_var.get(),
            "sharpen_amount": 1.0,
            "use_denoise": self.denoise_var.get(),
            "denoise_strength": 3,
            "pdf_dpi": int(self.dpi_var.get())
        }
        
        settings_path = Path("docscan_settings.json")
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)
        
        messagebox.showinfo("Settings Saved", f"Settings saved to {settings_path}")
    
    def load_settings(self):
        """Load settings from JSON file if it exists"""
        settings_path = Path("docscan_settings.json")
        if settings_path.exists():
            try:
                with open(settings_path, "r") as f:
                    saved_settings = json.load(f)
                    self.settings.update(saved_settings)
            except (json.JSONDecodeError, IOError):
                pass
    
    def save_image(self):
        """Save the current enhanced image"""
        if self.gray_img is None:
            messagebox.showerror("Error", "No image to save")
            return
        
        # Process image
        result = self.process_image(self.gray_img)
        
        # Get save path with format options
        save_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg"),
                ("PDF files", "*.pdf"),
                ("All files", "*.*")
            ]
        )
        
        if save_path:
            save_path = Path(save_path)
            dpi = int(self.dpi_var.get())
            
            if save_path.suffix.lower() == '.pdf':
                # Save as PDF
                pil_image = Image.fromarray(result)
                pil_image.save(save_path, "PDF", resolution=float(dpi))
            else:
                # Save as image
                cv2.imwrite(str(save_path), result)
            
            messagebox.showinfo("Image Saved", f"Enhanced image saved to {save_path}")
    
    def process_batch(self):
        """Process all selected files in batch"""
        if not self.batch_files:
            messagebox.showerror("Error", "No files selected for batch processing")
            return
        
        if self.is_processing:
            messagebox.showwarning("Processing", "Batch processing already in progress")
            return
        
        # Ask for output format
        format_window = tk.Toplevel(self.root)
        format_window.title("Batch Output")
        format_window.geometry("300x180")
        format_window.transient(self.root)
        format_window.grab_set()
        
        format_var = tk.StringVar(value="folder_png")
        
        ttk.Label(format_window, text="Select output format:").pack(pady=10)
        
        formats = [
            ("Folder with PNG files", "folder_png"),
            ("Folder with JPEG files", "folder_jpg"),
            ("Individual PDF files", "folder_pdf"),
            ("Combined PDF (single file)", "combined_pdf"),
            ("ZIP with PNG files", "zip_png"),
            ("ZIP with JPEG files", "zip_jpg")
        ]
        
        for text, value in formats:
            ttk.Radiobutton(format_window, text=text, variable=format_var, value=value).pack(anchor=tk.W, padx=20)
        
        def confirm_format():
            format_window.destroy()
            self.run_batch(format_var.get())
        
        ttk.Button(format_window, text="OK", command=confirm_format).pack(pady=10)
    
    def run_batch(self, output_format):
        """Run batch processing in a separate thread"""
        self.is_processing = True
        self.batch_btn.config(state=tk.DISABLED)
        self.progress_var.set(0)
        
        # Start processing thread
        thread = threading.Thread(
            target=self._batch_worker, 
            args=(output_format,),
            daemon=True
        )
        thread.start()
    
    def _batch_worker(self, output_format):
        """Worker thread for batch processing"""
        total = len(self.batch_files)
        processed = 0
        errors = []
        
        # Determine output location based on first file
        first_file = self.batch_files[0]
        
        if output_format == "combined_pdf":
            # Single PDF output - ask user for save location
            self.root.after(0, lambda: self._ask_combined_pdf_path())
            return
        
        # Create output folder next to first file
        output_dir = first_file.parent / f"{first_file.stem}_enhanced"
        output_dir.mkdir(exist_ok=True)
        
        # Check if we need a zip file
        create_zip = output_format.startswith("zip_")
        zip_path = None
        if create_zip:
            zip_path = first_file.parent / f"{first_file.stem}_enhanced.zip"
        
        pdf_images = []  # For combined PDF
        
        for file_path in self.batch_files:
            try:
                dpi_render = int(self.dpi_var.get())
                loaded = self.load_images_from_path(file_path, dpi=max(200, dpi_render))
                if not loaded:
                    errors.append(f"{file_path.name}: Could not read file")
                    continue
                for name, img in loaded:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    result = self.process_image(gray)
                    # Save based on format
                    if output_format in ("folder_png", "zip_png"):
                        out_path = output_dir / f"{name}_enhanced.png"
                        cv2.imwrite(str(out_path), result)
                    elif output_format in ("folder_jpg", "zip_jpg"):
                        out_path = output_dir / f"{name}_enhanced.jpg"
                        cv2.imwrite(str(out_path), result, [cv2.IMWRITE_JPEG_QUALITY, 95])
                    elif output_format == "folder_pdf":
                        out_path = output_dir / f"{name}_enhanced.pdf"
                        pil_image = Image.fromarray(result)
                        pil_image.save(str(out_path), "PDF", resolution=float(dpi_render))
                processed += 1
                self.root.after(0, lambda p=processed: self.progress_var.set((p / total) * 100))
            except Exception as e:
                errors.append(f"{file_path.name}: {str(e)}")
        
        # Create zip if requested
        if create_zip and zip_path:
            try:
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for file in output_dir.iterdir():
                        if file.is_file():
                            zf.write(file, file.name)
                
                # Clean up folder
                shutil.rmtree(output_dir)
            except Exception as e:
                errors.append(f"ZIP creation: {str(e)}")
        
        # Update UI on main thread
        self.root.after(0, self._batch_complete, processed, errors, str(output_dir if not create_zip else zip_path))
    
    def _ask_combined_pdf_path(self):
        """Ask user for combined PDF save location"""
        save_path = filedialog.asksaveasfilename(
            title="Save Combined PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        
        if save_path:
            thread = threading.Thread(
                target=self._batch_worker_combined_pdf,
                args=(Path(save_path),),
                daemon=True
            )
            thread.start()
        else:
            self.is_processing = False
            self.batch_btn.config(state=tk.NORMAL)
    
    def _batch_worker_combined_pdf(self, save_path):
        """Worker thread for combined PDF output"""
        total = len(self.batch_files)
        processed = 0
        errors = []
        pdf_images = []
        
        for file_path in self.batch_files:
            try:
                dpi_render = int(self.dpi_var.get())
                loaded = self.load_images_from_path(file_path, dpi=max(200, dpi_render))
                if not loaded:
                    errors.append(f"{file_path.name}: Could not read file")
                    continue
                for name, img in loaded:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    result = self.process_image(gray)
                    pil_image = Image.fromarray(result)
                    pdf_images.append(pil_image)
                processed += 1
                self.root.after(0, lambda p=processed: self.progress_var.set((p / total) * 100))
            except Exception as e:
                errors.append(f"{file_path.name}: {str(e)}")
        
        # Save combined PDF
        if pdf_images:
            try:
                dpi = int(self.dpi_var.get())
                pdf_images[0].save(
                    str(save_path), "PDF", resolution=float(dpi),
                    save_all=True, append_images=pdf_images[1:]
                )
            except Exception as e:
                errors.append(f"Combined PDF: {str(e)}")
        
        self.root.after(0, self._batch_complete, processed, errors, str(save_path))
    
    def _batch_complete(self, processed, errors, output_path):
        """Called when batch processing is complete"""
        self.is_processing = False
        self.batch_btn.config(state=tk.NORMAL)
        self.progress_var.set(100)
        
        # Show results
        message = f"Batch processing complete!\n\nProcessed: {processed}/{len(self.batch_files)} files"
        message += f"\n\nOutput: {output_path}"
        if errors:
            message += f"\n\nErrors ({len(errors)}):\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                message += f"\n... and {len(errors) - 5} more"
        
        messagebox.showinfo("Batch Complete", message)


def main():
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    
    app = DocScanGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
