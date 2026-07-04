class Counter(object):
    """用于统计指定姿态类别的重复次数，并判别不规范动作"""
    def __init__(self, class_name, enter_threshold=6, exit_threshold=4, min_duration=10):
        self._class_name = class_name  # 目标类别名称
        self._enter_threshold = enter_threshold  # 进入状态阈值
        self._exit_threshold = exit_threshold  # 退出状态阈值
        self._min_duration = min_duration  # 动作的最小持续帧数，用于判断动作是否规范
        self._pose_entered = False  # 当前是否处于该姿态状态
        self._n_repeats = 0  # 已记录的重复次数
        self._n_irregular = 0  # 已记录的不规范动作次数
        self._duration = 0  # 当前动作的持续帧数

    @property
    def n_repeats(self):
        return self._n_repeats

    @property
    def n_irregular(self):
        return self._n_irregular

    def __call__(self, pose_classification):
        """
        根据当前帧的分类结果判断是否完成一次重复，并判别不规范动作
        采用双阈值机制避免边界抖动导致误计数

        参数:
          pose_classification: 姿态分类结果字典，如:
            {'pushups_down': 8.3, 'pushups_up': 1.7}
        返回:
          当前累计的重复次数和不规范动作次数
        """
        pose_confidence = pose_classification.get(self._class_name, 0.0)

        if not self._pose_entered:
            if pose_confidence > self._enter_threshold:
                self._pose_entered = True
                self._duration = 1
            return self._n_repeats, self._n_irregular

        if pose_confidence < self._exit_threshold:
            if self._duration < self._min_duration:
                self._n_irregular += 1
            else:
                self._n_repeats += 1
            self._pose_entered = False
            self._duration = 0
        else:
            self._duration += 1

        return self._n_repeats, self._n_irregular