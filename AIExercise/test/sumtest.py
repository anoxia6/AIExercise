import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QComboBox, QSlider)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import mediapipe as mp

class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)
    status_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self._run_flag = True
        self.detection_confidence = 0.5
        self.tracking_confidence = 0.5
        
    def set_detection_confidence(self, value):
        self.detection_confidence = value
        
    def set_tracking_confidence(self, value):
        self.tracking_confidence = value
        
    def set_pose_option(self, option):
        self.pose_option = option
        
    def run(self):
        mp_pose = mp.solutions.pose
        mp_drawing = mp.solutions.drawing_utils
        
        pose = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=self.detection_confidence,
            min_tracking_confidence=self.tracking_confidence
        )
        
        cap = cv2.VideoCapture(21)
        
        if not cap.isOpened():
            self.status_signal.emit("Cannot open camera")
            return
            
        self.status_signal.emit("Pose detection started")
        
        while self._run_flag:
            ret, frame = cap.read()
            if not ret:
                self.status_signal.emit("Cannot read frame")
                break
                
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(rgb_frame)
            output_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
            
            if results.pose_landmarks:
                mp_drawing.draw_landmarks(
                    output_frame,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2)
                )
                
                landmark_count = len(results.pose_landmarks.landmark)
                cv2.putText(output_frame, f"Landmarks: {landmark_count}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            self.change_pixmap_signal.emit(output_frame)
            self.msleep(10)
        
        cap.release()
        pose.close()
        self.status_signal.emit("Pose detection stopped")
            
    def stop(self):
        self._run_flag = False
        self.wait()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("PyQt5 + OpenCV + Mediapipe Pose Detection")
        self.setMinimumSize(800, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Video display
        self.video_label = QLabel("Video will be displayed here")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("background-color: #000000;")
        main_layout.addWidget(self.video_label)
        
        # Control panel
        control_layout = QHBoxLayout()
        main_layout.addLayout(control_layout)
        
        # Pose option
        control_layout.addWidget(QLabel("Detection:"))
        self.pose_option_combo = QComboBox()
        self.pose_option_combo.addItems(["Upper Body", "Full Body"])
        self.pose_option_combo.currentTextChanged.connect(self.change_pose_option)
        control_layout.addWidget(self.pose_option_combo)
        
        # Confidence sliders
        self.create_slider(control_layout, "Detection", self.change_detection_confidence)
        self.create_slider(control_layout, "Tracking", self.change_tracking_confidence)
        
        # Control buttons
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.start_detection)
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_detection)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
        # Initialize thread
        self.thread = VideoThread()
        self.thread.change_pixmap_signal.connect(self.update_image)
        self.thread.status_signal.connect(self.update_status)
        
    def create_slider(self, layout, label_text, callback):
        """Helper method to create sliders"""
        label = QLabel(f"{label_text}: 0.5")
        layout.addWidget(label)
        
        slider = QSlider(Qt.Horizontal)
        slider.setRange(1, 10)
        slider.setValue(5)
        slider.valueChanged.connect(lambda value: self.update_slider(label, value, callback))
        layout.addWidget(slider)
        
        return slider
        
    def update_slider(self, label, value, callback):
        confidence = value / 10.0
        label.setText(f"{label.text().split(':')[0]}: {confidence:.1f}")
        callback(confidence)
        
    def start_detection(self):
        self.thread.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
    def stop_detection(self):
        self.thread.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
    def change_detection_confidence(self, value):
        self.thread.set_detection_confidence(value)
        
    def change_tracking_confidence(self, value):
        self.thread.set_tracking_confidence(value)
        
    def change_pose_option(self, option):
        self.thread.set_pose_option(option)
        self.statusBar().showMessage(f"Switched to {option} mode")
        
    def update_image(self, cv_img):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        q_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(q_image).scaled(
            self.video_label.width(), self.video_label.height(), Qt.KeepAspectRatio))
            
    def update_status(self, message):
        self.statusBar().showMessage(message)
        
    def closeEvent(self, event):
        self.thread.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())