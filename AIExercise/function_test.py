import cv2
import numpy as np
from PyQt5.QtGui import QImage, QPixmap
from mediapipe.python.solutions import drawing_utils as mp_drawing
from mediapipe.python.solutions import pose as mp_pose

from EMASmoothing import EMASmoothing
from PoseClassificationVisualizer import PoseClassificationVisualizer
from Counter import Counter
from PoseClassify import BodyPoseEmbedder, PoseClassifier

# 定义姿态计数函数
def PoseCount(pose_samples_folder, class_name):
    # 初始化姿态追踪器
    pose_tracker = mp_pose.Pose()
    print("初始化姿态追踪器")
    # 初始化姿态嵌入器
    pose_embedder = BodyPoseEmbedder()
    print("初始化姿态嵌入器")
    # 初始化姿态分类器
    pose_classifier = PoseClassifier(
        pose_samples_folder=pose_samples_folder,
        pose_embedder=pose_embedder,
        top_n_by_max_distance=30,
        top_n_by_mean_distance=10)
    print("初始化姿态分类器")
    # 初始化EMA平滑器
    pose_classification_filter = EMASmoothing(window_size=10, alpha=0.2)
    print("初始化EMA平滑器")
    # 初始化指定动作的计数器，设置进入和退出阈值
    repetition_counter = Counter(class_name=class_name, enter_threshold=6, exit_threshold=4)
    print("初始化计数器")
    # 初始化姿态分类可视化器
    pose_classification_visualizer = PoseClassificationVisualizer(class_name=class_name)
    print("初始化姿态分类可视化器")
    print("开始计数")
    # 计数信息
    infor = "计数："
    # 帧索引
    frame_idx = 0
    # 输出帧
    output_frame = None
    # 打开摄像头
    video_cap = cv2.VideoCapture(0)
    global i
    i = 0
    # 循环读取摄像头帧
    while video_cap.isOpened() & i == 0:
        # 读取下一帧
        success, input_frame = video_cap.read()
        if not success:
            print('忽略空的摄像头帧。')
            break
        if input_frame is not None:
            # 转换颜色空间
            input_frame = cv2.cvtColor(input_frame, cv2.COLOR_BGR2RGB)
            # 运行姿态追踪器
            result = pose_tracker.process(image=input_frame)
            pose_landmarks = result.pose_landmarks
            # 复制输入帧作为输出帧
            output_frame = input_frame.copy()
            if pose_landmarks is not None:
                # 绘制姿态预测结果
                mp_drawing.draw_landmarks(
                    image=output_frame,
                    landmark_list=pose_landmarks,
                    connections=mp_pose.POSE_CONNECTIONS)

            if pose_landmarks is not None:
                # 获取帧的高度和宽度
                frame_height, frame_width = output_frame.shape[0], output_frame.shape[1]
                # 提取姿态关键点坐标
                pose_landmarks = np.array(
                    [[lmk.x * frame_width, lmk.y * frame_height, lmk.z * frame_width] for lmk in
                     pose_landmarks.landmark],
                    dtype=np.float32)
                assert pose_landmarks.shape == (33, 3), '意外的关键点形状: {}'.format(pose_landmarks.shape)

                # 对当前帧的姿态进行分类
                pose_classification = pose_classifier(pose_landmarks)

                # 使用EMA平滑分类结果
                pose_classification_filtered = pose_classification_filter(pose_classification)

                # 计数重复次数
                repetitions_count = repetition_counter(pose_classification_filtered)
            else:
                # 没有检测到姿态，当前帧不进行分类
                pose_classification = None

                # 为未来帧进行平滑处理
                pose_classification_filtered = pose_classification_filter(dict())
                pose_classification_filtered = None

                # 获取最新的重复次数
                repetitions_count = repetition_counter.n_repeats
            # 更新计数信息
            infor1 = "当前计数：" + str(repetitions_count) + "个"
            if infor1 != infor:
                infor = infor1
                #ui.printstr(infor)
            frame_idx += 1
            # 可视化姿态分类结果
            output_frame = pose_classification_visualizer(
                frame=output_frame,
                pose_classification=pose_classification,
                pose_classification_filtered=pose_classification_filtered,
                repetitions_count=repetitions_count)
            # 转换颜色空间
            output_frame = cv2.cvtColor(np.array(output_frame), cv2.COLOR_BGR2RGB)
            # 调整输出帧的大小
            output_frame = cv2.resize(output_frame, dsize=(740, 480), dst=None, fx=2, fy=2,
                                      interpolation=cv2.INTER_NEAREST)
            h, w, ch = output_frame.shape
            bytes_per_line = ch * w
            q_image = QImage(output_frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
            q_pixmap = QPixmap.fromImage(q_image)
            # 显示输出帧
            cv2.imshow('Pose Classification', output_frame)
            # 按‘q’键退出循环
            if cv2.waitKey(1) == ord('q'):
                break
            #return q_pixmap
            

if __name__ == '__main__':
    # 姿态样本文件夹
    pose_samples_folder = 'squat_csvs_out'
    # 动作类别名称
    class_name = 'down'
    print("开始计数")
    # 调用姿态计数函数
    PoseCount(pose_samples_folder, class_name)
    #cv2.destroyAllWindows()