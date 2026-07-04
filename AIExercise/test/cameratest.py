import cv2
cap = cv2.VideoCapture(21)
if not cap.isOpened():
    print("摄像头无法打开")
while True:
    ret, frame = cap.read()
    if not ret:
        break
    cv2.imshow('test', frame)
    if cv2.waitKey(1) == ord('q'):
        break
cap.release()
cv2.destroyAllWindows()