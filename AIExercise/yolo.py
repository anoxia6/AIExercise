import gc
from ultralytics import YOLO
import cv2

class YOLODetector: 
    def __init__(self, model_path="./model/best.pt", conf_threshold=0.6, iou_threshold=0.45):
        """
        初始化YOLOv8目标检测器
        
        参数:
            model_path: 模型权重文件路径
            conf_threshold: 置信度阈值
            iou_threshold: 交并比阈值
        """
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.class_names = self.model.names  # 获取类别名称映射表
    
    def detect(self, frame):
        """
        对输入的视频帧进行目标检测
        
        参数:
            frame: 输入的视频帧，numpy数组格式 (H, W, C)
        
        返回:
            processed_frame: 处理后的视频帧，包含检测框和标签
            class_index: 第一个检测到的主要目标类别数字索引（置信度最高）
                         如果没有检测到目标，返回None
        """
        # 运行模型推理
        results = self.model(
            frame,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            verbose=False
        )
        
        # 获取第一个检测结果
        result = results[0]
        
        # 提取类别索引和置信度
        class_index = None
        if len(result.boxes) > 0:
            # 获取置信度最高的目标（默认第一个）
            box = result.boxes[0]
            class_index = int(box.cls)
            
            # 在原图上绘制检测结果
            processed_frame = frame.copy()
            
            # 获取边界框坐标
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
            
            # 获取置信度
            conf = float(box.conf)
            
            # 获取类别名称
            cls_name = self.class_names[class_index]
            
            # 绘制边界框
            cv2.rectangle(processed_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # 绘制标签
            label = f"{cls_name}: {conf:.2f}"
            cv2.putText(processed_frame, label, (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        else:
            # 如果没有检测到目标，返回原始帧和None
            processed_frame = frame.copy()
        
        return processed_frame, class_index
    
    def get_class_names(self):
        """获取类别名称映射表"""
        return self.class_names
    
    def release(self):
        """释放模型资源"""
        del self.model
        gc.collect()
    
class YOLOTracker:
    def __init__(self, detector, consecutive_frames=6):
        """
        初始化连续检测跟踪器
        
        参数:
            detector: YOLOv8Detector实例
            consecutive_frames: 需要连续检测到的帧数
        """
        self.detector = detector
        self.consecutive_frames = consecutive_frames
        
        # 滑动窗口：存储最近n帧的检测结果
        self.detection_history = []
        
        # 当前确认的检测结果
        self.current_detection = None
    
    def process_frame(self, frame):
        """
        处理单帧并跟踪连续检测
        
        参数:
            frame: 输入视频帧
            
        返回:
            processed_frame: 处理后的视频帧
            confirmed_class_index: 确认的类别索引（连续多帧出现）
                                   如果未确认，返回None
        """
        # 执行单帧检测
        processed_frame, class_index = self.detector.detect(frame)
        
        # 更新检测历史
        self.detection_history.append(class_index)
        
        # 保持滑动窗口大小固定
        if len(self.detection_history) > self.consecutive_frames:
            self.detection_history.pop(0)
        
        # 检查是否连续n帧检测到同一类别
        self.current_detection = self._check_consecutive_detections()
        
        return processed_frame, self.current_detection
    
    def _check_consecutive_detections(self):
        """检查滑动窗口中是否所有帧都检测到同一类别"""
        # 如果历史记录不足，返回None
        if len(self.detection_history) < self.consecutive_frames:
            return None
            
        # 获取最近n帧的检测结果
        recent_detections = self.detection_history[-self.consecutive_frames:]
        
        # 如果所有帧检测结果相同且不为None，则确认检测到
        first_detection = recent_detections[0]
        if first_detection is not None and all(d == first_detection for d in recent_detections):
            return first_detection
        
        return None
    
    def get_current_detection(self):
        """获取当前确认的检测结果"""
        return self.current_detection  
      