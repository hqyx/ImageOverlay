import sys
import os
import platform
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QFileDialog, 
                             QVBoxLayout, QHBoxLayout, QWidget, QSlider, QPushButton, QFrame, QMenu, QMessageBox)
from PyQt6.QtCore import Qt, QPoint, QEvent, QSize, QRect, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QAction, QIcon, QCursor, QColor, QPainter, QPalette, QTransform

# Platform-specific imports
import ctypes
try:
    from ctypes import wintypes
    import winreg
except ImportError:
    # Windows-specific modules might not be available on other platforms
    pass

def is_admin():
    if platform.system() == "Windows":
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    else:
        # On Unix-like systems
        try:
            return os.geteuid() == 0
        except:
            return False

def register_context_menu():
    if platform.system() != "Windows":
        # On macOS, "Open With" is handled by the OS and Info.plist in the app bundle.
        # We can show a message to the user.
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText("On macOS, please use Finder to set 'Open With' for image files.")
        msg.setWindowTitle("Context Menu Info")
        msg.exec()
        return

    exe_path = sys.executable
    # If we are running as a script, we might not want to register python.exe, 
    # but for the sake of the standalone app, sys.executable will be the ImageOverlay.exe
    
    if not is_admin():
        # Re-run with admin rights
        # We pass a special flag to know we should run registration
        print("Requesting admin privileges...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", exe_path, "--register-context-menu", None, 1)
        return

    key_path = r"*\shell\OpenWithImageOverlay"
    try:
        # Create the main key
        key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path)
        winreg.SetValue(key, "", winreg.REG_SZ, "Open with Image Overlay")
        winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key)

        # Create the command key
        command_key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path + r"\command")
        winreg.SetValue(command_key, "", winreg.REG_SZ, f'"{exe_path}" "%1"')
        winreg.CloseKey(command_key)
        
        # Show a message box? Since we are in a GUI app or transient process.
        # If this is a separate process, a simple ctypes messagebox works.
        ctypes.windll.user32.MessageBoxW(0, "Successfully added to right-click menu!", "Success", 0)
        
    except Exception as e:
        ctypes.windll.user32.MessageBoxW(0, f"Failed to register: {e}", "Error", 0)

class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(30)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 0, 0, 0)
        self.layout.setSpacing(0)

        # Menu Button
        self.btn_menu = QPushButton("☰")
        self.btn_menu.setFixedSize(30, 30)
        self.btn_menu.setStyleSheet("""
            QPushButton { background-color: transparent; color: #333; border: none; font-size: 16px; }
            QPushButton:hover { background-color: #ccc; }
        """)
        self.btn_menu.clicked.connect(self.show_menu)
        self.layout.insertWidget(0, self.btn_menu)

        # Title
        self.title_label = QLabel("Image Overlay")
        self.title_label.setStyleSheet("color: #333; font-weight: bold;")
        self.layout.addWidget(self.title_label)
        
        self.layout.addStretch()

        # Minimize Button
        self.btn_min = QPushButton("-")
        self.btn_min.setFixedSize(30, 30)
        self.btn_min.setStyleSheet("""
            QPushButton { background-color: transparent; color: #333; border: none; font-size: 16px; }
            QPushButton:hover { background-color: #ccc; }
        """)
        self.btn_min.clicked.connect(self.minimize_window)
        self.layout.addWidget(self.btn_min)

        # Close Button
        self.btn_close = QPushButton("×")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setStyleSheet("""
            QPushButton { background-color: transparent; color: #333; border: none; font-size: 20px; }
            QPushButton:hover { background-color: #d32f2f; color: white; }
        """)
        self.btn_close.clicked.connect(self.close_window)
        self.layout.addWidget(self.btn_close)

        # Dragging state
        self.start_pos = None
        self.click_pos = None

    def show_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #f0f0f0; color: #333; border: 1px solid #ccc; }
            QMenu::item { padding: 5px 20px; }
            QMenu::item:selected { background-color: #ddd; }
        """)
        
        action_add_context = QAction("Add to Right-Click Menu", self)
        action_add_context.triggered.connect(lambda: register_context_menu())
        menu.addAction(action_add_context)
        
        # Add Open File action
        action_open = QAction("Open Image...", self)
        action_open.triggered.connect(self.parent.open_file_dialog)
        menu.addAction(action_open)

        menu.exec(self.btn_menu.mapToGlobal(QPoint(0, self.btn_menu.height())))

    def minimize_window(self):
        self.parent.showMinimized()

    def close_window(self):
        self.parent.close()


    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.globalPosition().toPoint()
            self.click_pos = self.mapToGlobal(event.position().toPoint())
            self.parent_pos = self.parent.pos()

    def mouseMoveEvent(self, event):
        if self.start_pos:
            delta = event.globalPosition().toPoint() - self.start_pos
            self.parent.move(self.parent_pos + delta)

    def mouseReleaseEvent(self, event):
        self.start_pos = None


class ImageWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap = None
        self.opacity = 1.0
        self.setAcceptDrops(True)
        self.parent_window = parent

    def set_image(self, pixmap):
        self.pixmap = pixmap
        self.update()

    def set_opacity(self, opacity):
        self.opacity = opacity
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        if self.pixmap and not self.pixmap.isNull():
            # Draw image centered and maintaining aspect ratio
            target_rect = self.rect()
            
            # Set opacity
            painter.setOpacity(self.opacity)
            
            # Calculate the rectangle to draw the pixmap into, preserving aspect ratio
            # and centering it in the widget
            scaled_pixmap_rect = self.pixmap.scaled(
                target_rect.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            ).rect()
            
            # Center the rect
            scaled_pixmap_rect.moveCenter(target_rect.center())
            
            # Draw the pixmap into the calculated rect
            # Note: We need to draw the source pixmap scaled into the target rect
            # But QPainter.drawPixmap(rect, pixmap) stretches.
            # So we rely on the aspect ratio calculation we just did.
            # Actually, a better way with QPainter is:
            
            # Compute the aspect ratio correct rect
            img_w = self.pixmap.width()
            img_h = self.pixmap.height()
            widget_w = target_rect.width()
            widget_h = target_rect.height()
            
            scale = min(widget_w / img_w, widget_h / img_h)
            draw_w = int(img_w * scale)
            draw_h = int(img_h * scale)
            
            draw_x = int(target_rect.x() + (widget_w - draw_w) / 2)
            draw_y = int(target_rect.y() + (widget_h - draw_h) / 2)
            
            draw_rect = QRect(draw_x, draw_y, draw_w, draw_h)
            
            painter.drawPixmap(draw_rect, self.pixmap)
        else:
            # Draw placeholder text
            painter.setPen(QColor("#666"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Drag & Drop Image Here")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if self.parent_window:
                self.parent_window.load_image(file_path)


class ImageOverlayApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Image Overlay")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Default window size
        self.resize(500, 400)

        # Main Layout
        self.central_widget = QWidget()
        # Set almost transparent background for central widget to ensure mouse events are captured
        # in the resize margin area.
        self.central_widget.setStyleSheet("background-color: rgba(255, 255, 255, 0.01);")
        self.setCentralWidget(self.central_widget)
        
        # Use a frame for the visible border
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(5, 5, 5, 5) # Margin for resize handles
        self.main_layout.setSpacing(0)

        # Container Frame (The "Opaque Border" look)
        self.container_frame = QFrame()
        # Initial state: Opaque background because no image is loaded yet.
        self.container_frame.setStyleSheet("background-color: #f0f0f0; border: 4px solid #d0d0d0; border-radius: 0px;")
        self.container_layout = QVBoxLayout(self.container_frame)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)
        
        self.main_layout.addWidget(self.container_frame)

        # Title Bar
        self.title_bar = TitleBar(self)
        # Title Bar needs its own opaque background
        self.title_bar.setStyleSheet("background-color: #f0f0f0;")
        self.container_layout.addWidget(self.title_bar)

        # Image Area
        self.image_widget = ImageWidget(self)
        self.container_layout.addWidget(self.image_widget)

        # Slider Overlay (Floating or docked?)
        # Let's put it in a bottom bar for "Traditional" look or overlay?
        # User said "Like traditional software... Close Minimize etc". 
        # Usually traditional software has controls. Let's put a bottom control bar.
        
        self.bottom_bar = QWidget()
        self.bottom_bar.setFixedHeight(35) # Fixed compact height
        self.bottom_bar.setStyleSheet("background-color: #f0f0f0;")
        self.bottom_layout = QHBoxLayout(self.bottom_bar)
        self.bottom_layout.setContentsMargins(5, 0, 5, 0)
        self.bottom_layout.setSpacing(10)
        
        # Rotation Buttons
        self.btn_rotate_ccw = QPushButton("↺")
        self.btn_rotate_ccw.setFixedSize(30, 25)
        self.btn_rotate_ccw.setToolTip("Rotate Left")
        self.btn_rotate_ccw.clicked.connect(lambda: self.rotate_image(-90))
        self.bottom_layout.addWidget(self.btn_rotate_ccw)
        
        self.btn_rotate_cw = QPushButton("↻")
        self.btn_rotate_cw.setFixedSize(30, 25)
        self.btn_rotate_cw.setToolTip("Rotate Right")
        self.btn_rotate_cw.clicked.connect(lambda: self.rotate_image(90))
        self.bottom_layout.addWidget(self.btn_rotate_cw)

        # Opacity Slider
        self.opacity_label = QLabel("Opacity:")
        self.opacity_label.setStyleSheet("color: #333;")
        self.bottom_layout.addWidget(self.opacity_label)

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self.change_opacity)
        self.opacity_slider.setStyleSheet("""
            QSlider::groove:horizontal { border: 1px solid #ccc; height: 6px; background: #e0e0e0; margin: 2px 0; border-radius: 3px; }
            QSlider::handle:horizontal { background: #fff; border: 1px solid #999; width: 14px; height: 14px; margin: -4px 0; border-radius: 7px; }
        """)
        self.bottom_layout.addWidget(self.opacity_slider)
        
        self.container_layout.addWidget(self.bottom_bar)

        # Resize Logic
        self.resizing = False
        self.dragging = False
        self.resize_edge = None
        self.resize_margin = 10
        self.start_pos = None
        self.drag_start_pos = None
        self.window_start_pos = None
        self.start_geometry = None
        self.aspect_ratio = None  # To store image aspect ratio
        self.setMouseTracking(True)
        self.central_widget.setMouseTracking(True)
        self.container_frame.setMouseTracking(True)
        self.image_widget.setMouseTracking(True)

        # Install event filter to handle dragging from anywhere
        self.central_widget.installEventFilter(self)
        self.container_frame.installEventFilter(self)
        self.image_widget.installEventFilter(self)
        self.bottom_bar.installEventFilter(self)
        self.opacity_label.installEventFilter(self)

        # Load initial image
        if len(sys.argv) > 1:
            file_path = sys.argv[1]
            if os.path.exists(file_path):
                self.load_image(file_path)

    def load_image(self, file_path):
        image = QImage(file_path)
        if image.isNull():
            return

        if image.format() not in [QImage.Format.Format_ARGB32, QImage.Format.Format_ARGB32_Premultiplied]:
            image = image.convertToFormat(QImage.Format.Format_ARGB32)

        pixmap = QPixmap.fromImage(image)
        self.image_widget.set_image(pixmap)
        self.title_bar.title_label.setText(os.path.basename(file_path))
        
        # Store aspect ratio (width / height)
        if pixmap.height() > 0:
            self.aspect_ratio = pixmap.width() / pixmap.height()
        
        # Change background to transparent (visually hidden) but keeping the frame visible
        # The user wants the background to be transparent so they can see through it.
        # We use rgba(255, 255, 255, 0.01) (1% opacity white) to ensure the window still captures 
        # mouse events (drag/drop) on Windows with WA_TranslucentBackground.
        # Note: '1' in rgba usually means 100% opacity in some contexts if interpreted as integer,
        # so we use 0.01 to be safe and ensure it is effectively invisible.
        self.container_frame.setStyleSheet("background-color: rgba(255, 255, 255, 0.01); border: 4px solid #d0d0d0; border-radius: 0px;")

        # Resize window to fit image + decorations
        # Title Bar (30) + Bottom Bar (Dynamic) 
        # Container Border (4px * 2 = 8px vertical, 8px horizontal)
        # Main Layout margins (5px * 2 = 10px)
        
        extra_w = 18
        
        # Calculate extra_h dynamically
        title_h = self.title_bar.height()
        bottom_h = self.bottom_bar.height()
        if bottom_h < 35: bottom_h = 35 # Use fixed height for fallback
            
        extra_h = title_h + bottom_h + 18
        
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            # Use 85% of screen size as maximum to ensure borders are visible
            max_w = screen_geo.width() * 0.85
            max_h = screen_geo.height() * 0.85
            
            # Calculate max allowable image size
            max_img_w = max_w - extra_w
            max_img_h = max_h - extra_h
            
            img_w = pixmap.width()
            img_h = pixmap.height()
            
            # Calculate scale to fit within max dimensions while maintaining aspect ratio
            scale_w = max_img_w / img_w if img_w > 0 else 1
            scale_h = max_img_h / img_h if img_h > 0 else 1
            
            # Use the smaller scale factor to ensure it fits in both dimensions
            # If scale > 1 (image is smaller than max), use 1.0 to keep original size
            # If scale < 1 (image is larger than max), use scale to shrink
            scale = min(scale_w, scale_h)
            if scale > 1.0:
                scale = 1.0
                
            target_w = int(img_w * scale + extra_w)
            target_h = int(img_h * scale + extra_h)
            
            self.resize(target_w, target_h)
            
            # Center the window on screen
            x = screen_geo.x() + (screen_geo.width() - target_w) // 2
            y = screen_geo.y() + (screen_geo.height() - target_h) // 2
            self.move(x, y)
        else:
            # Fallback if no screen info
            target_w = pixmap.width() + extra_w
            target_h = pixmap.height() + extra_h
            self.resize(target_w, target_h)

    def rotate_image(self, angle):
        if not self.image_widget.pixmap or self.image_widget.pixmap.isNull():
            return

        # Rotate the pixmap
        transform = QTransform().rotate(angle)
        new_pixmap = self.image_widget.pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        self.image_widget.set_image(new_pixmap)

        # Update aspect ratio
        if new_pixmap.height() > 0:
            self.aspect_ratio = new_pixmap.width() / new_pixmap.height()

        # Adjust window dimensions to match rotation (swap content width/height)
        geo = self.geometry()
        w = geo.width()
        h = geo.height()
        
        # Calculate chrome dimensions
        extra_w = 18
        title_h = self.title_bar.height()
        bottom_h = self.bottom_bar.height()
        if bottom_h < 35: bottom_h = 35
        extra_h = title_h + bottom_h + 18
        
        # Current content size
        content_w = max(1, w - extra_w)
        content_h = max(1, h - extra_h)
        
        # Calculate scale based on aspect ratio to ensure we don't distort
        # Actually, we just want to swap the bounding box of the content?
        # If we rotate 90deg, the new content width should be old content height * (something?)
        # No, if we physically rotate the image, the image width becomes height, height becomes width.
        # So we should just swap content_w and content_h.
        
        # But wait, if the window was resized to not match the image aspect ratio (e.g. with black bars or empty space),
        # simply swapping might be weird.
        # But let's assume the user wants to see the image.
        
        new_content_w = content_h
        new_content_h = content_w
        
        # Calculate new window size
        new_w = new_content_w + extra_w
        new_h = new_content_h + extra_h
        
        # Ensure it fits on screen
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            # If too big, scale down maintaining new aspect ratio
            if new_w > screen_geo.width() or new_h > screen_geo.height():
                 scale_w = screen_geo.width() / new_w
                 scale_h = screen_geo.height() / new_h
                 scale = min(scale_w, scale_h, 1.0)
                 new_w = int(new_w * scale)
                 new_h = int(new_h * scale)
        
        # Center on previous center
        center = geo.center()
        new_geo = QRect(0, 0, new_w, new_h)
        new_geo.moveCenter(center)
        
        # Ensure top-left is on screen
        if new_geo.left() < screen_geo.left(): new_geo.moveLeft(screen_geo.left())
        if new_geo.top() < screen_geo.top(): new_geo.moveTop(screen_geo.top())
        
        self.setGeometry(new_geo)

    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if file_path:
            self.load_image(file_path)

    def change_opacity(self, value):
        # Only change the image opacity, not the window
        opacity = value / 100.0
        self.image_widget.set_opacity(opacity)

    # --- Manual Resize Logic ---
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self.handle_mouse_press(event.globalPosition().toPoint())
                return True
        elif event.type() == QEvent.Type.MouseMove:
            self.handle_mouse_move(event.globalPosition().toPoint())
            # We consume mouse move to ensure custom cursor and drag works consistently
            # across all filtered widgets.
            return True
        elif event.type() == QEvent.Type.MouseButtonRelease:
            if event.button() == Qt.MouseButton.LeftButton:
                self.handle_mouse_release()
                return True
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.handle_mouse_press(event.globalPosition().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.handle_mouse_move(event.globalPosition().toPoint())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.handle_mouse_release()
        super().mouseReleaseEvent(event)

    def handle_mouse_press(self, global_pos):
        local_pos = self.mapFromGlobal(global_pos)
        edge = self.get_resize_edge(local_pos)
        if edge:
            self.resizing = True
            self.resize_edge = edge
            self.start_pos = global_pos
            self.start_geometry = self.geometry()
        else:
            self.dragging = True
            self.drag_start_pos = global_pos
            self.window_start_pos = self.pos()

    def handle_mouse_move(self, global_pos):
        if self.resizing:
            self.handle_resize(global_pos)
        elif self.dragging:
            delta = global_pos - self.drag_start_pos
            self.move(self.window_start_pos + delta)
        else:
            local_pos = self.mapFromGlobal(global_pos)
            self.update_cursor(local_pos)

    def handle_mouse_release(self):
        self.resizing = False
        self.dragging = False
        self.resize_edge = None
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def get_resize_edge(self, pos):
        x = pos.x()
        y = pos.y()
        w = self.width()
        h = self.height()
        m = self.resize_margin

        edge = 0
        # 1: Left, 2: Right, 4: Top, 8: Bottom
        if x < m: edge |= 1
        elif x > w - m: edge |= 2
        if y < m: edge |= 4
        elif y > h - m: edge |= 8
        
        return edge

    def update_cursor(self, pos):
        edge = self.get_resize_edge(pos)
        if edge == 1 or edge == 2:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif edge == 4 or edge == 8:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif edge == 5 or edge == 10: # TopLeft or BottomRight
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif edge == 6 or edge == 9: # TopRight or BottomLeft
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def handle_resize(self, global_pos):
        if not self.resizing:
            return

        diff = global_pos - self.start_pos
        geo = self.start_geometry
        new_geo = QRect(geo)

        # 1: Left, 2: Right, 4: Top, 8: Bottom
        # Calculate rough new geometry first
        if self.resize_edge & 1: # Left
            new_geo.setLeft(geo.left() + diff.x())
        elif self.resize_edge & 2: # Right
            new_geo.setRight(geo.right() + diff.x())
        
        if self.resize_edge & 4: # Top
            new_geo.setTop(geo.top() + diff.y())
        elif self.resize_edge & 8: # Bottom
            new_geo.setBottom(geo.bottom() + diff.y())

        # Enforce Aspect Ratio if image is loaded
        if self.aspect_ratio:
            # If dragging a corner, we prioritize Width or Height based on movement?
            # Or simpler: Prioritize Width change for Left/Right edges, Height for Top/Bottom.
            # For corners, let's drive by Width.
            
            # Calculate current content area size (excluding chrome)
            # But here we are resizing the whole window.
            # The image aspect ratio applies to the image area.
            # However, our layout has fixed margins/chrome.
            # TitleBar (30) + BottomBar (30) + Borders (8) = 68 vertical extra
            # Borders (8) = 8 horizontal extra (Wait, in load_image we used 18 and 78?)
            # Let's re-check load_image calc:
            # target_w = pixmap.width() + 18
            # target_h = pixmap.height() + 78
            # So Extra_W = 18, Extra_H = 78
            
            extra_w = 18
            extra_h = 78
            
            # Get new proposed dimensions
            w = new_geo.width()
            h = new_geo.height()
            
            # content_w / content_h = aspect_ratio
            # (w - extra_w) / (h - extra_h) = aspect_ratio
            
            # If resizing Left/Right (Edge 1 or 2), Width drives Height
            if self.resize_edge in [1, 2]:
                target_content_w = w - extra_w
                if target_content_w < 1: target_content_w = 1
                target_content_h = target_content_w / self.aspect_ratio
                new_h = int(target_content_h + extra_h)
                new_geo.setHeight(new_h)
                
            # If resizing Top/Bottom (Edge 4 or 8), Height drives Width
            elif self.resize_edge in [4, 8]:
                target_content_h = h - extra_h
                if target_content_h < 1: target_content_h = 1
                target_content_w = target_content_h * self.aspect_ratio
                new_w = int(target_content_w + extra_w)
                new_geo.setWidth(new_w)
                
            # If resizing Corner, use the dominant axis to drive the resize
            else:
                # Calculate the change in dimensions proposed by the mouse movement
                delta_w = abs(new_geo.width() - geo.width())
                delta_h = abs(new_geo.height() - geo.height())
                
                # Compare deltas to decide which axis drives.
                # We normalize delta_h to width space for comparison: delta_h * aspect_ratio
                # If delta_w > delta_h * aspect_ratio, width change is more significant.
                
                if delta_w > delta_h * self.aspect_ratio:
                    # Width drives Height
                    target_content_w = w - extra_w
                    if target_content_w < 1: target_content_w = 1
                    target_content_h = target_content_w / self.aspect_ratio
                    new_h = int(target_content_h + extra_h)
                    
                    if self.resize_edge & 4: # Top
                        new_geo.setTop(new_geo.bottom() - new_h + 1)
                    else: # Bottom
                        new_geo.setHeight(new_h)
                else:
                    # Height drives Width
                    target_content_h = h - extra_h
                    if target_content_h < 1: target_content_h = 1
                    target_content_w = target_content_h * self.aspect_ratio
                    new_w = int(target_content_w + extra_w)
                    
                    if self.resize_edge & 1: # Left
                        new_geo.setLeft(new_geo.right() - new_w + 1)
                    else: # Right
                        new_geo.setWidth(new_w)

        # Minimum size check
        if new_geo.width() < 100:
            new_geo.setWidth(100)
        if new_geo.height() < 100:
            new_geo.setHeight(100)

        self.setGeometry(new_geo)


class ImageApplication(QApplication):
    file_opened = pyqtSignal(str)

    def event(self, event):
        if event.type() == QEvent.Type.FileOpen:
            # event.file() returns the file path as a string
            self.file_opened.emit(event.file())
            return True
        return super().event(event)


if __name__ == "__main__":
    try:
        if "--register-context-menu" in sys.argv:
            register_context_menu()
            sys.exit()

        app = ImageApplication(sys.argv)
        window = ImageOverlayApp()
        
        # Connect signal for macOS file open
        app.file_opened.connect(window.load_image)
        
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        with open("error_log.txt", "w") as f:
            f.write(str(e))
            import traceback
            f.write(traceback.format_exc())
        # Also try to show a message box if possible, but might fail if app not init
        try:
            if platform.system() == "Windows":
                ctypes.windll.user32.MessageBoxW(0, f"Error: {e}", "Startup Error", 0)
            else:
                # Fallback for other platforms if QApplication not running? 
                # If we can't use Qt, we might just print to stderr.
                print(f"Startup Error: {e}", file=sys.stderr)
        except:
            pass
        sys.exit(1)
