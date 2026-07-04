from PyQt5.QtCore import QTime, pyqtSignal
from PyQt5.QtWidgets import QDialog, QDialogButtonBox
from Ui_CountDialog import Ui_countDialog
from Ui_TimerDialog import Ui_timerDialog  

class CountDialog(QDialog):
    """计数对话框类"""
    count_set_signal = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_countDialog()
        self.ui.setupUi(self)
        
        self.ui.buttonBox.button(QDialogButtonBox.Ok).clicked.connect(self.on_ok_clicked)
        self.ui.buttonBox.button(QDialogButtonBox.Cancel).clicked.connect(self.reject)
    
    def get_selected_count(self):
        """获取用户选择的计数"""
        return self.ui.setcountspinBox.value()
    
    def on_ok_clicked(self):
        """OK按钮点击时的处理"""
        selected_count = self.get_selected_count()
        self.count_set_signal.emit(selected_count)
        print(f"Selected count: {selected_count}")
        self.accept()
        self.close()
    
    def reject(self):
        return super().reject()
    
class TimerDialog(QDialog):
    timer_set_signal = pyqtSignal(QTime)
    
    """定时对话框类"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_timerDialog()
        self.ui.setupUi(self)
        
        self.ui.buttonBox.button(QDialogButtonBox.Ok).clicked.connect(self.on_ok_clicked)
        self.ui.buttonBox.button(QDialogButtonBox.Cancel).clicked.connect(self.reject)
    
    def get_selected_time(self):
        """获取用户选择的时间"""
        return self.ui.settimeEdit.time()
    
    def on_ok_clicked(self):
        """OK按钮点击时的处理"""
        selected_time = self.get_selected_time()
        self.timer_set_signal.emit(selected_time)
        print(f"Selected time: {selected_time.toString()}")
        self.accept()
        self.close()
        
    def reject(self):
        return super().reject()