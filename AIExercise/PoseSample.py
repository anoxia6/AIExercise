class PoseSample(object):
    def __init__(self, name, landmarks, class_name, embedding):
        self.name = name
        self.landmarks = landmarks  # 原始关键点坐标
        self.class_name = class_name
        self.embedding = embedding  # 特征向量

class PoseSampleOutlier(object):
    """表示姿态分类中的异常样本"""
    def __init__(self, sample, detected_class, all_classes):
        self.sample = sample  # PoseSample对象
        self.detected_class = detected_class  # 模型预测的类别
        self.all_classes = all_classes  # 所有候选类别
