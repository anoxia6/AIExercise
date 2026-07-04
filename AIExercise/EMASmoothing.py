class EMASmoothing(object):
    """对姿态分类结果进行指数移动平均（EMA）平滑"""
    def __init__(self, window_size=10, alpha=0.2):
        self._window_size = window_size  # EMA计算使用的时间窗口大小
        self._alpha = alpha  # EMA衰减系数
        self._data_in_window = []  # 存储历史数据窗口

    def __call__(self, data):
        """
        对输入的姿态分类结果进行EMA平滑
        EMA公式: S_t = α * x_t + (1 - α) * S_{t-1}

        参数:
          data: 当前帧的分类结果字典
        返回:
          平滑后的分类结果字典
        """
        self._data_in_window.insert(0, data)
        self._data_in_window = self._data_in_window[:self._window_size]

        keys = set([key for data in self._data_in_window for key in data])

        smoothed_data = dict()
        for key in keys:
            factor = 1.0
            top_sum = 0.0
            bottom_sum = 0.0
            for data in self._data_in_window:
                value = data.get(key, 0.0)
                top_sum += factor * value
                bottom_sum += factor
                factor *= (1.0 - self._alpha)
            smoothed_data[key] = top_sum / bottom_sum
        return smoothed_data
