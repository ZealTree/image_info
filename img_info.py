import sys
import os
import time
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, 
                            QWidget, QPushButton, QFileDialog, QTextEdit, 
                            QScrollArea, QHBoxLayout)
from PyQt6.QtGui import QImage, QPixmap, QMovie, QColorSpace
from PyQt6.QtCore import Qt, QFileInfo
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import json

class ImageInfoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Advanced Image Metadata Viewer")
        self.setGeometry(100, 100, 1000, 800)
        self.current_file_path = None
        
        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Image preview
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedHeight(350)
        self.image_label.setStyleSheet("border: 1px solid black;")
        main_layout.addWidget(self.image_label)
        
        # Button row
        button_layout = QHBoxLayout()
        
        self.load_button = QPushButton("Load Image")
        self.load_button.clicked.connect(self.load_image)
        button_layout.addWidget(self.load_button)
        
        self.export_button = QPushButton("Export Raw Data")
        self.export_button.clicked.connect(self.export_raw_data)
        self.export_button.setEnabled(False)
        button_layout.addWidget(self.export_button)
        
        main_layout.addLayout(button_layout)
        
        # Text area for image info
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setStyleSheet("""
            font-family: Consolas, monospace; 
            font-size: 12px;
            color: #333;
        """)
        
        # Add scroll area
        scroll = QScrollArea()
        scroll.setWidget(self.info_text)
        scroll.setWidgetResizable(True)
        main_layout.addWidget(scroll)
        
        # Initialize variables
        self.current_image = None
        self.current_movie = None
        self.raw_exif_data = None
    
    def load_image(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, 
            "Open Image File", 
            "", 
            "Images (*.bmp *.png *.jpg *.jpeg *.gif *.webp *.tiff *.heic)"
        )
        
        if file_path:
            self.current_file_path = file_path
            self.display_image_info(file_path)
            self.export_button.setEnabled(True)
    
    def export_raw_data(self):
        if not self.current_file_path or not self.raw_exif_data:
            return
            
        file_dialog = QFileDialog()
        save_path, _ = file_dialog.getSaveFileName(
            self,
            "Save Raw Data",
            "",
            "Text Files (*.txt)"
        )
        
        if save_path:
            try:
                with open(save_path, 'w') as f:
                    f.write(f"Image Path: {self.current_file_path}\n")
                    f.write("="*50 + "\n")
                    f.write("RAW EXIF DATA:\n")
                    f.write(json.dumps(self.raw_exif_data, indent=4))
                self.info_text.append("\nRaw data exported successfully!")
            except Exception as e:
                self.info_text.append(f"\nExport error: {str(e)}")
    
    def display_image_info(self, file_path):
        self.info_text.clear()
        self.raw_exif_data = None
        
        # Stop animation if any
        if self.current_movie:
            self.current_movie.stop()
            self.image_label.setMovie(None)
            self.current_movie = None
        
        # Try to load as QImage first
        self.current_image = QImage(file_path)
        
        if self.current_image.isNull():
            if file_path.lower().endswith('.gif'):
                self.handle_gif_file(file_path)
                return
            self.info_text.setText("Failed to load image.")
            return
        
        self.show_image_preview()
        self.show_file_metadata(file_path)
        self.show_image_metadata(file_path)
        self.show_advanced_metadata(file_path)
    
    def handle_gif_file(self, file_path):
        self.current_movie = QMovie(file_path)
        if self.current_movie.isValid():
            self.image_label.setMovie(self.current_movie)
            self.current_movie.start()
            self.display_gif_info(file_path)
        else:
            self.info_text.setText("Failed to load GIF animation.")

    def show_image_preview(self):
        pixmap = QPixmap.fromImage(self.current_image)
        scaled_pixmap = pixmap.scaled(
            self.image_label.width(), 
            self.image_label.height(), 
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)

    def show_file_metadata(self, file_path):
        file_info = QFileInfo(file_path)
        info = "=== FILE METADATA ===\n"
        info += f"• Path: {file_path}\n"
        info += f"• Name: {os.path.basename(file_path)}\n"
        info += f"• Size: {self.format_size(file_info.size())}\n"
        info += f"• Created: {file_info.birthTime().toString() if file_info.birthTime().isValid() else 'Unknown'}\n"
        info += f"• Modified: {file_info.lastModified().toString()}\n"
        info += f"• Accessed: {file_info.lastRead().toString()}\n\n"
        self.info_text.insertPlainText(info)

    def show_image_metadata(self, file_path):
        info = "=== IMAGE PROPERTIES ===\n"
        info += f"• Dimensions: {self.current_image.width()} × {self.current_image.height()} px\n"
        info += f"• Color depth: {self.current_image.depth()} bits\n"
        info += f"• Format: {str(self.current_image.format())}\n"
        
        color_space = self.current_image.colorSpace()
        if color_space.isValid():
            info += f"• Color space: {color_space.description()}\n"
        
        info += f"• Alpha channel: {'Yes' if self.current_image.hasAlphaChannel() else 'No'}\n"
        
        if self.current_image.dotsPerMeterX() > 0:
            dpi_x = self.current_image.dotsPerMeterX() / 39.37
            dpi_y = self.current_image.dotsPerMeterY() / 39.37
            info += f"• Resolution: {dpi_x:.1f} × {dpi_y:.1f} DPI\n"
        
        self.info_text.insertPlainText(info)

    def show_advanced_metadata(self, file_path):
        try:
            with Image.open(file_path) as img:
                info = "\n=== ADVANCED METADATA ===\n"
                info += f"• PIL format: {img.format}\n"
                info += f"• Color mode: {img.mode}\n"
                
                # Get and store raw EXIF data
                self.raw_exif_data = self.get_raw_exif_data(img)
                
                # EXIF data processing
                exif = self.get_exif_data(img)
                if exif:
                    info += "\nEXIF DATA:\n"
                    for tag, value in exif.items():
                        if tag == "GPSInfo":
                            info += self.format_gps_info(value)
                        else:
                            info += f"• {tag}: {value}\n"
                
                # Format-specific metadata
                if img.format == 'PNG' and hasattr(img, 'info'):
                    info += "\nPNG METADATA:\n"
                    for k, v in img.info.items():
                        if isinstance(k, str):
                            info += f"• {k}: {v}\n"
                
                self.info_text.insertPlainText(info)
        except Exception as e:
            self.info_text.insertPlainText(f"\nMETADATA ERROR: {str(e)}\n")

    def get_raw_exif_data(self, pil_image):
        """Get complete raw EXIF data for export"""
        try:
            exif_data = {}
            raw_exif = pil_image.getexif()
            if not raw_exif:
                return None

            for tag_id, value in raw_exif.items():
                tag_name = TAGS.get(tag_id, tag_id)
                exif_data[tag_name] = str(value) if not isinstance(value, (bytes, dict)) else "binary/data"
            
            return exif_data
        except Exception:
            return None

    def get_exif_data(self, pil_image):
        """Safe EXIF data extraction with GPS handling"""
        try:
            exif_data = {}
            raw_exif = pil_image.getexif()
            if not raw_exif:
                return None

            for tag_id, value in raw_exif.items():
                tag_name = TAGS.get(tag_id, tag_id)
                
                if tag_name == "GPSInfo":
                    exif_data[tag_name] = self.parse_gps_info(value)
                else:
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8', errors='replace')
                        except:
                            value = str(value)
                    exif_data[tag_name] = value
            
            return exif_data
        except Exception:
            return None

    def parse_gps_info(self, gps_info):
        """Robust GPS info parser"""
        if not gps_info:
            return None
        
        try:
            gps_data = {}
            for tag_id in gps_info:
                tag_name = GPSTAGS.get(tag_id, f"Tag_{tag_id}")
                value = gps_info[tag_id]
                
                # Handle coordinate tuples
                if tag_name in ['GPSLatitude', 'GPSLongitude']:
                    if isinstance(value, tuple) and len(value) == 3:
                        gps_data[tag_name] = self.format_dms(value)
                        # Add corresponding Ref tag
                        ref_tag = tag_name + 'Ref'
                        ref_value = gps_info.get(tag_id + 1, '?')
                        gps_data[ref_tag] = ref_value
                    else:
                        gps_data[tag_name] = f"Unsupported format: {value}"
                else:
                    gps_data[tag_name] = value
            
            # Convert to decimal coordinates if possible
            if 'GPSLatitude' in gps_data and 'GPSLongitude' in gps_data:
                try:
                    lat = self.dms_to_decimal(gps_data['GPSLatitude'], 
                                           gps_data.get('GPSLatitudeRef', 'N'))
                    lon = self.dms_to_decimal(gps_data['GPSLongitude'],
                                           gps_data.get('GPSLongitudeRef', 'E'))
                    
                    if lat is not None and lon is not None:
                        gps_data['Decoded'] = f"{lat:.6f}, {lon:.6f}"
                        gps_data['Map'] = f"https://www.google.com/maps?q={lat},{lon}"
                except Exception as e:
                    gps_data['DecodeError'] = f"Coord conversion failed: {str(e)}"

            return gps_data
        except Exception as e:
            return {"Error": f"Full parsing failed: {str(e)}", 
                    "RawData": str(gps_info)}

    def format_dms(self, dms_tuple):
        """Format degrees/minutes/seconds"""
        if not isinstance(dms_tuple, tuple) or len(dms_tuple) != 3:
            return str(dms_tuple)
        
        # Handle rational numbers (common in EXIF)
        def to_float(val):
            return float(val.numerator / val.denominator) if hasattr(val, 'numerator') else float(val)
        
        degrees = to_float(dms_tuple[0])
        minutes = to_float(dms_tuple[1])
        seconds = to_float(dms_tuple[2])
        
        return f"{degrees:.0f}° {minutes:.0f}' {seconds:.2f}\""

    def dms_to_decimal(self, dms, ref):
        """Convert DMS to decimal degrees"""
        try:
            # Handle string format (e.g. "45°30'12.34\"")
            if isinstance(dms, str):
                parts = dms.replace('°', ' ').replace('\'', ' ').replace('"', ' ').split()
                degrees = float(parts[0])
                minutes = float(parts[1]) if len(parts) > 1 else 0
                seconds = float(parts[2]) if len(parts) > 2 else 0
            # Handle tuple format (degrees, minutes, seconds)
            elif isinstance(dms, tuple) and len(dms) == 3:
                degrees = dms[0]
                minutes = dms[1]
                seconds = dms[2]
                
                # Convert rational numbers to float if needed
                if hasattr(degrees, 'numerator'):
                    degrees = float(degrees.numerator / degrees.denominator)
                if hasattr(minutes, 'numerator'):
                    minutes = float(minutes.numerator / minutes.denominator)
                if hasattr(seconds, 'numerator'):
                    seconds = float(seconds.numerator / seconds.denominator)
            else:
                return None
            
            decimal = degrees + minutes/60 + seconds/3600
            if ref in ('S', 'W'):
                decimal = -decimal
            return decimal
        except Exception:
            return None

    def format_gps_info(self, gps_data):
        """Format GPS info for display"""
        if not gps_data:
            return "• GPS Info: No data\n"
        
        if isinstance(gps_data, str):
            return f"• GPS Info: {gps_data}\n"
        
        info = ""
        if 'Decoded' in gps_data:
            info += f"• Coordinates: {gps_data['Decoded']}\n"
            info += f"• Google Maps: {gps_data['Map']}\n"
        
        for tag, value in gps_data.items():
            if tag not in ('Decoded', 'Map'):
                info += f"• GPS {tag}: {value}\n"
        
        return info

    def display_gif_info(self, file_path):
        info = "\n=== GIF PROPERTIES ===\n"
        info += f"• Frame count: {self.current_movie.frameCount()}\n"
        info += f"• Speed: {self.current_movie.speed()}%\n"
        info += f"• Background: {self.current_movie.backgroundColor().name()}\n"
        
        # Basic image properties
        temp_image = QImage(file_path)
        if not temp_image.isNull():
            info += f"\n• Dimensions: {temp_image.width()} × {temp_image.height()} px\n"
            info += f"• Color depth: {temp_image.depth()} bits\n"
        
        # PIL info
        try:
            with Image.open(file_path) as img:
                info += f"\n• PIL format: {img.format}\n"
                info += f"• Frame count: {getattr(img, 'n_frames', 1)}\n"
                if hasattr(img, 'info'):
                    for k, v in img.info.items():
                        if isinstance(v, (str, int, float)):
                            info += f"• {k}: {v}\n"
        except Exception as e:
            info += f"\n• PIL Error: {str(e)}\n"
        
        self.info_text.insertPlainText(info)

    def format_size(self, bytes):
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024.0:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024.0
        return f"{bytes:.2f} TB"

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageInfoApp()
    window.show()
    sys.exit(app.exec())