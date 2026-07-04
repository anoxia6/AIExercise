import cv2
import numpy as np
import gc
from rknnlite.api import RKNNLite
from rk3588_hw import rga_helper

class YOLODetector:
    def __init__(self, model_path="./model/yolov8.rknn", conf_threshold=0.85, iou_threshold=0.45):
        """
        初始化YOLOv8目标检测器（基于rknnkit_lite）
        
        参数:
            model_path: RKNN模型权重文件路径
            conf_threshold: 置信度阈值
            iou_threshold: 交并比阈值
        """
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        
        # 加载RKNN模型
        self.rknn_lite = RKNNLite()
        self._load_model()
        
        # 类别名称（COCO数据集）
        self.class_names = (
            "squat", "bicycle", "car", "motorbike", "aeroplane", "bus", "train", "truck", "boat",
            "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
            "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
            "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
            "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
            "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
            "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
            "sofa", "pottedplant", "bed", "diningtable", "toilet", "tvmonitor", "laptop", "mouse",
            "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator",
            "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
        )
        
        # 模型输入尺寸
        self.input_size = (640, 640)
        self.letterbox_helper = self._init_letterbox_helper()

    def _load_model(self):
        """加载并初始化RKNN模型"""
        print(f"--> 加载RKNN模型: {self.model_path}")
        ret = self.rknn_lite.load_rknn(self.model_path)
        if ret != 0:
            print(f"加载模型失败: {ret}")
            raise Exception("模型加载失败")
        print("模型加载成功")
        
        print("--> 初始化运行环境")
        ret = self.rknn_lite.init_runtime(core_mask=RKNNLite.NPU_CORE_0)
        if ret != 0:
            print(f"初始化运行环境失败: {ret}")
            raise Exception("运行环境初始化失败")
        print("运行环境初始化成功")

    def _init_letterbox_helper(self):
        """初始化图像预处理工具"""
        class LetterBoxHelper:
            def __init__(self, input_size):
                self.pad_w = 0
                self.pad_h = 0
                self.scale = 1.0
                self.input_size = input_size  # 存储输入尺寸
            
            def letter_box(self, im, new_shape=None, pad_color=(0, 0, 0)):
                if new_shape is None:
                    new_shape = self.input_size
                h, w = im.shape[:2]
                new_w, new_h = new_shape
                r = min(new_w / w, new_h / h)
                self.scale = r
                nw, nh = int(w * r), int(h * r)
                self.pad_w, self.pad_h = (new_w - nw) // 2, (new_h - nh) // 2
                
                im_resized = rga_helper.resize(im, (nw, nh))
                im_padded = np.full((new_h, new_w, 3), pad_color, dtype=np.uint8)
                im_padded[self.pad_h:self.pad_h + nh, self.pad_w:self.pad_w + nw, :] = im_resized
                return np.ascontiguousarray(im_padded)
            
            def get_real_box(self, boxes):
                if boxes is None or len(boxes) == 0:
                    return boxes
                    
                real_boxes = []
                for box in boxes:
                    x1, y1, x2, y2 = box
                    x1 = max(0, x1 - self.pad_w)
                    y1 = max(0, y1 - self.pad_h)
                    x2 = min(self.input_size[0] - self.pad_w * 2, x2 - self.pad_w)
                    y2 = min(self.input_size[1] - self.pad_h * 2, y2 - self.pad_h)
                    x1, y1, x2, y2 = [int(coord / self.scale) for coord in [x1, y1, x2, y2]]
                    real_boxes.append([x1, y1, x2, y2])
                return np.array(real_boxes)
        
        # 实例化时传入input_size
        return LetterBoxHelper(self.input_size)

    def dfl(self, position):
        """Distribution Focal Loss解码（纯NumPy实现）"""
        n, c, h, w = position.shape
        p_num = 4
        mc = c // p_num
        y = position.reshape(n, p_num, mc, h, w)
        
        y_max = np.max(y, axis=2, keepdims=True)
        y_exp = np.exp(y - y_max)
        y = y_exp / np.sum(y_exp, axis=2, keepdims=True)
        
        acc_metrix = np.arange(mc).reshape(1, 1, mc, 1, 1).astype(np.float32)
        y = np.sum(y * acc_metrix, axis=2)
        return y

    def post_process(self, outputs):
        """解析模型输出，提取检测结果"""
        if outputs is None or len(outputs) == 0:
            return None, None, None
            
        boxes, scores, classes_conf = [], [], []
        default_branch = 3
        if len(outputs) % default_branch != 0:
            return None, None, None
            
        pair_per_branch = len(outputs) // default_branch
        
        for i in range(default_branch):
            position = outputs[pair_per_branch * i]
            if position.ndim != 4:
                return None, None, None
                
            grid_h, grid_w = position.shape[2:4]
            col, row = np.meshgrid(np.arange(grid_w), np.arange(grid_h))
            grid = np.concatenate((col.reshape(1, 1, grid_h, grid_w), row.reshape(1, 1, grid_h, grid_w)), axis=1)
            stride = np.array([self.input_size[1] // grid_h, self.input_size[0] // grid_w]).reshape(1, 2, 1, 1)
            
            position = self.dfl(position)
            box_xy = grid + 0.5 - position[:, 0:2, :, :]
            box_xy2 = grid + 0.5 + position[:, 2:4, :, :]
            xyxy = np.concatenate((box_xy * stride, box_xy2 * stride), axis=1)
            boxes.append(xyxy.transpose(0, 2, 3, 1).reshape(-1, 4))
            
            if pair_per_branch * i + 1 >= len(outputs):
                return None, None, None
            classes_conf.append(outputs[pair_per_branch * i + 1].transpose(0, 2, 3, 1).reshape(-1, len(self.class_names)))
            scores.append(np.ones((boxes[-1].shape[0], 1), dtype=np.float32))
        
        if not boxes or not classes_conf or not scores:
            return None, None, None
            
        boxes = np.concatenate(boxes, axis=0)
        classes_conf = np.concatenate(classes_conf, axis=0)
        scores = np.concatenate(scores, axis=0).flatten()
        
        class_max_score = np.max(classes_conf, axis=-1)
        classes = np.argmax(classes_conf, axis=-1)
        keep = (class_max_score * scores) >= self.conf_threshold
        boxes = boxes[keep]
        scores = (class_max_score * scores)[keep]
        classes = classes[keep]
        
        if len(boxes) == 0:
            return None, None, None
            
        keep = self.nms(boxes, scores)
        return boxes[keep], classes[keep], scores[keep]

    def nms(self, boxes, scores):
        """非极大值抑制"""
        if boxes is None or len(boxes) == 0:
            return []
            
        x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        order = scores.argsort()[::-1]
        keep = []
        
        while order.size > 0:
            i = order[0]
            keep.append(i)
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            w = np.maximum(0, xx2 - xx1 + 1)
            h = np.maximum(0, yy2 - yy1 + 1)
            inter = w * h
            ovr = inter / (areas[i] + areas[order[1:]] - inter)
            order = order[np.where(ovr <= self.iou_threshold)[0] + 1]
        return keep

    def detect(self, frame):
        """
        对输入帧进行目标检测
        
        参数:
            frame: 输入视频帧 (H, W, C)
            
        返回:
            processed_frame: 带检测框的帧
            class_index: 置信度最高的类别索引（无检测时返回None）
        """
        if frame is None:
            return None, None
            
        # 1. 图像预处理
        frame = np.ascontiguousarray(frame)
        img = self.letterbox_helper.letter_box(frame)
        img = rga_helper.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = np.expand_dims(np.ascontiguousarray(img), 0).astype(np.float32)
        
        # 2. 模型推理
        try:
            outputs = self.rknn_lite.inference(inputs=[img])
        except Exception as e:
            print(f"推理错误: {e}")
            return frame, None
            
        # 3. 后处理
        boxes, classes, scores = self.post_process(outputs)
        
        # 4. 映射到原始尺寸并绘制结果
        processed_frame = frame.copy()
        class_index = None
        
        if boxes is not None and len(boxes) > 0:
            # 获取置信度最高的目标
            max_idx = np.argmax(scores)
            box = boxes[max_idx]
            cls = classes[max_idx]
            score = scores[max_idx]
            
            # 映射到原始尺寸
            real_box = self.letterbox_helper.get_real_box([box])[0]
            x1, y1, x2, y2 = real_box
            
            # 绘制边界框
            cv2.rectangle(processed_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # 绘制标签
            label = f"{self.class_names[cls]}: {score:.2f}"
            cv2.putText(
                processed_frame, label, (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2
            )
            
            class_index = cls
            
        return processed_frame, class_index

    def get_class_names(self):
        """获取类别名称映射表"""
        return self.class_names

    def release(self):
        """释放模型资源"""
        if hasattr(self, 'rknn_lite'):
            self.rknn_lite.release()
            del self.rknn_lite
            gc.collect()


class YOLOTracker:
    def __init__(self, detector, consecutive_frames=80):
        """
        初始化连续检测跟踪器
        
        参数:
            detector: YOLODetector实例
            consecutive_frames: 需要连续检测到的帧数
        """
        self.detector = detector
        self.consecutive_frames = consecutive_frames
        self.detection_history = []
        self.current_detection = None

    def process_frame(self, frame):
        """
        处理单帧并跟踪连续检测
        
        参数:
            frame: 输入视频帧
            
        返回:
            processed_frame: 处理后的视频帧
            confirmed_class_index: 确认的类别索引（连续多帧出现）
        """
        # 执行单帧检测
        processed_frame, class_index = self.detector.detect(frame)
        
        # 更新检测历史
        self.detection_history.append(class_index)
        
        # 保持滑动窗口大小
        if len(self.detection_history) > self.consecutive_frames:
            self.detection_history.pop(0)
        
        # 检查连续检测
        self.current_detection = self._check_consecutive_detections()
        
        return processed_frame, self.current_detection

    def _check_consecutive_detections(self):
        """检查是否连续n帧检测到同一类别"""
        if len(self.detection_history) < self.consecutive_frames:
            return None
            
        recent_detections = self.detection_history[-self.consecutive_frames:]
        first_det = recent_detections[0]
        
        if first_det is not None and all(d == first_det for d in recent_detections):
            return first_det
            
        return None

    def get_current_detection(self):
        """获取当前确认的检测结果"""
        return self.current_detection

    def release(self):
        """释放资源"""
        self.detector.release()
