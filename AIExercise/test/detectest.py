import os
import time
import cv2
import sys
import argparse
import numpy as np
from rknnlite.api import RKNNLite

# 修复日志配置冲突
import logging
logging.addLevelName(logging.WARNING, 'WARN')  # 将'WARNING'映射到'WARN'

# 检测参数配置
OBJ_THRESH = 0.25  # 目标置信度阈值
NMS_THRESH = 0.45  # NMS非极大值抑制阈值
INPUT_SIZE = (640, 640)  # 模型输入尺寸 (width, height)
DISPLAY_SIZE = (640, 480)  # 显示窗口尺寸 (width, height)

# COCO数据集类别
CLASSES = (
    "person", "bicycle", "car", "motorbike", "aeroplane", "bus", "train", "truck", "boat",
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

class LetterBoxHelper:
    def __init__(self, enable_letter_box=True):
        self.enable_letter_box = enable_letter_box
        self.pad_w = 0
        self.pad_h = 0
        self.scale = 1.0

    def letter_box(self, im, new_shape=INPUT_SIZE, pad_color=(0, 0, 0)):
        """保持比例缩放图像并填充黑边"""
        h, w = im.shape[:2]
        new_w, new_h = new_shape
        r = min(new_w / w, new_h / h)
        self.scale = r
        nw, nh = int(w * r), int(h * r)
        self.pad_w, self.pad_h = (new_w - nw) // 2, (new_h - nh) // 2
        im_resized = cv2.resize(im, (nw, nh))
        im_padded = np.full((new_h, new_w, 3), pad_color, dtype=np.uint8)
        im_padded[self.pad_h:self.pad_h + nh, self.pad_w:self.pad_w + nw, :] = im_resized
        return im_padded

    def get_real_box(self, boxes):
        """将缩放后的检测框映射回原始图像尺寸"""
        if boxes is None or len(boxes) == 0:
            return boxes
            
        real_boxes = []
        for box in boxes:
            x1, y1, x2, y2 = box
            
            # 去除填充区域
            x1 = max(0, x1 - self.pad_w)
            y1 = max(0, y1 - self.pad_h)
            x2 = min(INPUT_SIZE[0] - self.pad_w * 2, x2 - self.pad_w)
            y2 = min(INPUT_SIZE[1] - self.pad_h * 2, y2 - self.pad_h)
            
            # 映射到原始图像尺寸
            x1, y1, x2, y2 = [int(coord / self.scale) for coord in [x1, y1, x2, y2]]
            real_boxes.append([x1, y1, x2, y2])
        
        return np.array(real_boxes)

def dfl(position):
    """Distribution Focal Loss解码（预测框偏移量计算）"""
    # 使用纯NumPy实现替代PyTorch
    n, c, h, w = position.shape
    p_num = 4  # 4个坐标（x1, y1, x2, y2）
    mc = c // p_num
    y = position.reshape(n, p_num, mc, h, w)
    
    # 实现softmax函数
    y_max = np.max(y, axis=2, keepdims=True)
    y_exp = np.exp(y - y_max)  # 数值稳定性处理
    y = y_exp / np.sum(y_exp, axis=2, keepdims=True)
    
    # 加权求和得到最终偏移量
    acc_metrix = np.arange(mc).reshape(1, 1, mc, 1, 1).astype(np.float32)
    y = np.sum(y * acc_metrix, axis=2)
    
    return y

def post_process(input_data):
    """后处理：解析模型输出，生成检测框、类别和置信度"""
    # 添加输入有效性检查
    if input_data is None or len(input_data) == 0:
        print("❌ 模型推理输出为空，可能是推理失败")
        return None, None, None
    
    boxes, scores, classes_conf = [], [], []
    default_branch = 3  # YOLOv8通常有3个输出分支
    
    # 检查输出分支数量是否符合预期
    if len(input_data) % default_branch != 0:
        print(f"❌ 模型输出分支数量异常：{len(input_data)}，预期应为{default_branch}的倍数")
        return None, None, None
    
    pair_per_branch = len(input_data) // default_branch
    
    # 解析每个分支的输出
    for i in range(default_branch):
        # 解析边界框
        position = input_data[pair_per_branch * i]
        # 添加维度检查
        if position.ndim != 4:
            print(f"❌ 边界框输出维度异常：{position.shape}，预期为4维")
            return None, None, None
        grid_h, grid_w = position.shape[2:4]
        col, row = np.meshgrid(np.arange(grid_w), np.arange(grid_h))
        grid = np.concatenate((col.reshape(1, 1, grid_h, grid_w), row.reshape(1, 1, grid_h, grid_w)), axis=1)
        stride = np.array([INPUT_SIZE[1] // grid_h, INPUT_SIZE[0] // grid_w]).reshape(1, 2, 1, 1)
        
        # DFL解码 + 计算实际坐标
        position = dfl(position)
        box_xy = grid + 0.5 - position[:, 0:2, :, :]
        box_xy2 = grid + 0.5 + position[:, 2:4, :, :]
        xyxy = np.concatenate((box_xy * stride, box_xy2 * stride), axis=1)
        boxes.append(xyxy.transpose(0, 2, 3, 1).reshape(-1, 4))  # 展平为(N,4)
        
        # 解析类别置信度和目标置信度
        if pair_per_branch * i + 1 >= len(input_data):
            print(f"❌ 类别置信度输出索引越界：{pair_per_branch * i + 1} >= {len(input_data)}")
            return None, None, None
        classes_conf.append(input_data[pair_per_branch * i + 1].transpose(0, 2, 3, 1).reshape(-1, len(CLASSES)))
        scores.append(np.ones((boxes[-1].shape[0], 1), dtype=np.float32))  # 目标置信度初始化为1

    # 合并所有分支结果
    if not boxes or not classes_conf or not scores:
        print("❌ 分支结果为空")
        return None, None, None
    boxes = np.concatenate(boxes, axis=0)
    classes_conf = np.concatenate(classes_conf, axis=0)
    scores = np.concatenate(scores, axis=0).flatten()

    # 过滤低置信度框
    class_max_score = np.max(classes_conf, axis=-1)
    classes = np.argmax(classes_conf, axis=-1)
    keep = (class_max_score * scores) >= OBJ_THRESH
    boxes = boxes[keep]
    scores = (class_max_score * scores)[keep]
    classes = classes[keep]

    # NMS非极大值抑制
    if len(boxes) == 0:
        return None, None, None
    keep = nms(boxes, scores)
    return boxes[keep], classes[keep], scores[keep]

def nms(boxes, scores):
    """非极大值抑制：去除重叠框"""
    if boxes is None or len(boxes) == 0:
        return []
        
    x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]  # 按置信度降序排序
    keep = []
    
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1, yy1 = np.maximum(x1[i], x1[order[1:]]), np.maximum(y1[i], y1[order[1:]])
        xx2, yy2 = np.minimum(x2[i], x2[order[1:]]), np.minimum(y2[i], y2[order[1:]])
        w, h = np.maximum(0, xx2 - xx1 + 1), np.maximum(0, yy2 - yy1 + 1)
        inter = w * h
        ovr = inter / (areas[i] + areas[order[1:]] - inter)
        order = order[np.where(ovr <= NMS_THRESH)[0] + 1]
    return keep

def draw_result(img, boxes, classes, scores, fps=None):
    """在图像上绘制检测结果"""
    if boxes is None or len(boxes) == 0:
        # 绘制无检测结果提示
        cv2.putText(
            img, "No detections", (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2
        )
        return img
        
    for box, cl, score in zip(boxes, classes, scores):
        x1, y1, x2, y2 = map(int, box)
        # 绘制边界框
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        # 绘制类别和置信度
        label = f"{CLASSES[cl]} {score:.2f}"
        cv2.putText(
            img, label, (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2
        )
    
    # 绘制FPS信息
    if fps is not None:
        cv2.putText(
            img, f"FPS: {fps:.2f}", (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2
        )
    
    return img

def process_video(rknn_lite, video_path, show=True, save=False, output_path="./output.mp4"):
    """处理视频流（摄像头或本地文件）"""
    # 打开视频源
    cap = cv2.VideoCapture(
        int(video_path) if video_path.isdigit() else video_path
    )
    if not cap.isOpened():
        print(f"❌ 无法打开视频源：{video_path}")
        return

    # 获取视频属性
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"📹 视频源信息：{width}x{height} @ {fps:.2f} FPS")
    
    # 初始化视频写入器（如果需要保存）
    video_writer = None
    if save:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        print(f"📝 视频将保存至：{output_path}")

    co_helper = LetterBoxHelper()
    frame_count = 0
    start_time = time.time()
    
    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print("\n📌 视频流结束")
                break

            frame_count += 1
            if frame_count % 10 == 0:  # 每10帧打印一次进度
                print(f"处理帧：{frame_count} | 分辨率：{width}x{height}", end="\r")

            # 1. 预处理：缩放并填充图像
            img = co_helper.letter_box(
                im=frame.copy(),
                new_shape=INPUT_SIZE,  # (width, height)
                pad_color=(0, 0, 0)
            )
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # BGR转RGB
            img = np.expand_dims(img, 0).astype(np.float32)  # 添加批次维度

            # 2. 模型推理（RK3588 NPU）
            outputs = rknn_lite.inference(inputs=[img])
            
            # 检查推理结果
            if outputs is None or len(outputs) == 0:
                print("❌ 模型推理失败，输出为空")
                continue

            # 3. 后处理：解析检测结果
            boxes, classes, scores = post_process(outputs)

            # 4. 映射检测框到原始图像
            if boxes is not None:
                boxes = co_helper.get_real_box(boxes)

            # 5. 计算FPS
            current_time = time.time()
            fps = frame_count / (current_time - start_time)

            # 6. 绘制结果
            result_frame = draw_result(frame.copy(), boxes, classes, scores, fps=fps)

            # 7. 显示或保存
            if show:
                # 调整显示尺寸
                display_frame = cv2.resize(result_frame, DISPLAY_SIZE)
                cv2.imshow("RK3588 NPU", display_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):  # 按q退出
                    break
            if save and video_writer is not None:
                video_writer.write(result_frame)

    finally:
        # 释放资源
        cap.release()
        if video_writer is not None:
            video_writer.release()
        cv2.destroyAllWindows()
        print("\n✅ 资源已释放")


if __name__ == '__main__':
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="RK3588 NPU 视频流检测工具")
    parser.add_argument("--model_path", type=str, required=True, help="RKNN模型路径（.rknn）")
    parser.add_argument("--video_path", type=str, required=True, help="视频源（摄像头填0，文件填路径）")
    parser.add_argument("--no_show", action="store_true", help="不显示实时画面")
    parser.add_argument("--save", action="store_true", help="保存检测结果视频")
    parser.add_argument("--output_path", type=str, default="./output.mp4", help="输出视频路径")
    args = parser.parse_args()

    # 检查文件是否存在
    if not os.path.exists(args.model_path):
        print(f"❌ 模型文件不存在：{args.model_path}")
        exit(-1)

    rknn_lite = RKNNLite()

    # Load RKNN model
    print('--> Load RKNN model')
    ret = rknn_lite.load_rknn(args.model_path)
    if ret != 0:
        print('Load RKNN model failed')
        exit(ret)
    print('done')

    # Init runtime environment
    print('--> Init runtime environment')
    ret = rknn_lite.init_runtime(core_mask=RKNNLite.NPU_CORE_0)
    if ret != 0:
        print('Init runtime environment failed')
        exit(ret)
    print('done')

    # Process video
    process_video(
        rknn_lite,
        video_path=args.video_path,
        show=not args.no_show,
        save=args.save,
        output_path=args.output_path
    )

    rknn_lite.release()