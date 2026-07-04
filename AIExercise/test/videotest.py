import sys
import cv2
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QThread, pyqtSignal

class VideoThread(QThread):

    change_pixmap_signal = pyqtSignal(QImage)
    
    def run(self):

        cap = cv2.VideoCapture(21)
        while True:
            ret, frame = cap.read()
            if ret:
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                p = convert_to_Qt_format.scaled(640, 480, Qt.KeepAspectRatio)
                self.change_pixmap_signal.emit(p)
        
        cap.release()

class CameraApp(QWidget):

    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 640, 480)
        

        self.image_label = QLabel(self)
        self.image_label.resize(640, 480)
        self.image_label.setAlignment(Qt.AlignCenter)
        #self.image_label.setText("������������ͷ...")

        layout = QVBoxLayout()
        layout.addWidget(self.image_label)
        self.setLayout(layout)
        

        self.thread = VideoThread()
        self.thread.change_pixmap_signal.connect(self.update_image)
        self.thread.start()
    
    def update_image(self, img):
        self.image_label.setPixmap(QPixmap.fromImage(img))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CameraApp()
    window.show()
    sys.exit(app.exec_())    