import sys
import os
import time
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, 
                            QWidget, QPushButton, QFileDialog, QTextEdit, 
                            QScrollArea)
from PyQt6.QtGui import QImage, QPixmap, QMovie
from PyQt6.QtCore import Qt, QFileInfo
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

class ImageInfoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Advanced Image Metadata Viewer with GPS")
        self.setGeometry(100, 100, 1000, 800)
        
        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Image preview
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedHeight(350)
        self.image_label.setStyleSheet("border: 1px solid black;")
        layout.addWidget(self.image_label)
        
        # Button to load image
        self.load_button = QPushButton("Load Image")
        self.load_button.clicked.connect(self.load_image)
        layout.addWidget(self.load_button)
        
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
        layout.addWidget(scroll)
        
        # Initialize variables
        self.current_image = None
        self.current_movie = None
    
    def load_image(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, 
            "Open Image File", 
            "", 
            "Images (*.bmp *.png *.jpg *.jpeg *.gif *.webp *.tiff *.heic)"
        )
        
        if file_path:
            self.display_image_info(file_path)
    
    def display_image_info(self, file_path):
        self.info_text.clear()
        
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
                
                # EXIF data processing
                exif = self.get_exif_data(img)
                if exif:
                    info += "\nEXIF DATA:\n"
                    for tag, value in exif.items():
                        if tag == "GPSInfo":
                            info += self.format_gps_info(value)
                        else:
                            info += f"• {tag}: {value}\n"
                
                # PNG specific
                if img.format == 'PNG' and hasattr(img, 'info'):
                    info += "\nPNG METADATA:\n"
                    for k, v in img.info.items():
                        if isinstance(k, str):
                            info += f"• {k}: {v}\n"
                
                self.info_text.insertPlainText(info)
        except Exception as e:
            self.info_text.insertPlainText(f"\nMETADATA ERROR: {str(e)}\n")

    def get_exif_data(self, pil_image):
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
        """Улучшенный парсер GPS данных с обработкой сырых значений"""
        if not gps_info:
            return "No GPS Data"
        
        # Если пришел просто числовой код (как 3051)
        if isinstance(gps_info, int):
            return f"Raw GPS Code: {gps_info} (Need special decoding)"
        
        try:
            gps_data = {}
            for tag_id in gps_info:
                tag_name = GPSTAGS.get(tag_id, f"UnknownTag_{tag_id}")
                value = gps_info[tag_id]
                
                # Особый случай: координаты хранятся как кортежи
                if tag_name in ['GPSLatitude', 'GPSLongitude'] and isinstance(value, tuple):
                    value = self.format_dms_coordinates(value)
                
                gps_data[tag_name] = value
            
            # Декодируем координаты, если они есть
            if 'GPSLatitude' in gps_data and 'GPSLongitude' in gps_data:
                lat = self.convert_to_decimal(gps_data['GPSLatitude'], 
                                        gps_data.get('GPSLatitudeRef', 'N'))
                lon = self.convert_to_decimal(gps_data['GPSLongitude'],
                                        gps_data.get('GPSLongitudeRef', 'E'))
                
                if lat is not None and lon is not None:
                    gps_data['DecodedCoordinates'] = f"{lat:.6f}, {lon:.6f}"
                    gps_data['GoogleMapsLink'] = f"https://www.google.com/maps?q={lat},{lon}"
            
            return gps_data
        
        except Exception as e:
            return f"GPS Data (Partial decode error: {str(e)})"

    def format_dms_coordinates(self, dms_tuple):
        """Форматирует координаты в градусы/минуты/секунды"""
        if not isinstance(dms_tuple, tuple) or len(dms_tuple) != 3:
            return str(dms_tuple)
        
        degrees, minutes, seconds = dms_tuple
        return f"{int(degrees)}°{int(minutes)}'{float(seconds):.2f}\""

    def convert_to_decimal(self, coord, direction):
        """Конвертирует DMS в десятичные градусы"""
        try:
            if isinstance(coord, str):
                # Пытаемся распарсить строковое представление
                parts = coord.replace('°', ' ').replace('\'', ' ').replace('"', ' ').split()
                degrees = float(parts[0])
                minutes = float(parts[1]) if len(parts) > 1 else 0
                seconds = float(parts[2]) if len(parts) > 2 else 0
            elif isinstance(coord, tuple) and len(coord) == 3:
                degrees, minutes, seconds = coord
            else:
                return None
            
            decimal = degrees + minutes/60 + seconds/3600
            if direction in ('S', 'W'):
                decimal = -decimal
            return decimal
        except:
            return None

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