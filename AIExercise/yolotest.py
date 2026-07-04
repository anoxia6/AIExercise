import cv2
import time
from collections import deque
from yolo_rknn import YOLODetector, YOLOTracker  # 假设你将类保存为 yolov8_rknn_detector.py

DISPLAY_SIZE = (640, 480)  # 控制显示分辨率


def run_video_demo(video_source=0, model_path="./model/yolov8.rknn", show=True, consecutive_frames=10):
    detector = YOLODetector(model_path=model_path)
    tracker = YOLOTracker(detector=detector, consecutive_frames=consecutive_frames)

    cap = cv2.VideoCapture(int(video_source) if str(video_source).isdigit() else video_source)
    if not cap.isOpened():
        print(f"❌ 无法打开视频源: {video_source}")
        return

    frame_count = 0
    start_time = time.time()

    print("🎬 正在处理视频流... 按 'q' 退出")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("\n📌 视频结束或读取失败")
                break

            processed_frame, confirmed_cls = tracker.process_frame(frame)

            # 显示识别类别（连续确认）
            if confirmed_cls is not None:
                label_text = f"✅ 连续识别：{detector.class_names[confirmed_cls]}"
                cv2.putText(
                    processed_frame, label_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2
                )

            # 显示FPS
            frame_count += 1
            elapsed = time.time() - start_time
            fps = frame_count / elapsed
            cv2.putText(
                processed_frame, f"FPS: {fps:.2f}", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
            )

            if show:
                display_frame = cv2.resize(processed_frame, DISPLAY_SIZE)
                cv2.imshow("RKNN YOLOv8 Tracker", display_frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("\n👋 用户退出")
                    break

    finally:
        cap.release()
        tracker.release()
        cv2.destroyAllWindows()
        print("✅ 资源释放完毕")


if __name__ == "__main__":
    run_video_demo(video_source=0, model_path="./model/yolov8.rknn")
