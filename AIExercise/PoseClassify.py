import csv
import numpy as np
import os
from PoseSample import PoseSample, PoseSampleOutlier

class BodyPoseEmbedder(object):
    """将3D姿态关键点转换为归一化的特征向量"""

    def __init__(self, torso_size_multiplier=2.5):
        self._torso_size_multiplier = torso_size_multiplier
        self._landmark_names = [
            'nose', 'left_eye_inner', 'left_eye', 'left_eye_outer',
            'right_eye_inner', 'right_eye', 'right_eye_outer',
            'left_ear', 'right_ear', 'mouth_left', 'mouth_right',
            'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
            'left_wrist', 'right_wrist', 'left_pinky_1', 'right_pinky_1',
            'left_index_1', 'right_index_1', 'left_thumb_2', 'right_thumb_2',
            'left_hip', 'right_hip', 'left_knee', 'right_knee',
            'left_ankle', 'right_ankle', 'left_heel', 'right_heel',
            'left_foot_index', 'right_foot_index',
        ]

    def __call__(self, landmarks):
        """归一化关键点并计算特征向量"""
        assert landmarks.shape[0] == len(self._landmark_names)
        landmarks = np.copy(landmarks)
        landmarks = self._normalize_pose_landmarks(landmarks)
        embedding = self._get_pose_distance_embedding(landmarks)
        return embedding

    def _normalize_pose_landmarks(self, landmarks):
        """平移至髋部中心，按躯干尺度归一化"""
        landmarks = np.copy(landmarks)
        pose_center = self._get_pose_center(landmarks)
        landmarks -= pose_center
        pose_size = self._get_pose_size(landmarks, self._torso_size_multiplier)
        landmarks /= pose_size
        landmarks *= 100  # 便于调试
        return landmarks

    def _get_pose_center(self, landmarks):
        """髋部中心 = 左右髋中点"""
        left_hip = landmarks[self._landmark_names.index('left_hip')]
        right_hip = landmarks[self._landmark_names.index('right_hip')]
        return (left_hip + right_hip) * 0.5

    def _get_pose_size(self, landmarks, torso_size_multiplier):
        """姿态尺寸 = max(躯干长度×系数, 所有关键点到中心的最大距离)"""
        landmarks = landmarks[:, :2]
        hips = np.mean([landmarks[self._landmark_names.index('left_hip')],
                        landmarks[self._landmark_names.index('right_hip')]], axis=0)
        shoulders = np.mean([landmarks[self._landmark_names.index('left_shoulder')],
                             landmarks[self._landmark_names.index('right_shoulder')]], axis=0)
        torso_size = np.linalg.norm(shoulders - hips)
        pose_center = self._get_pose_center(landmarks)
        max_dist = np.max(np.linalg.norm(landmarks - pose_center, axis=1))
        return max(torso_size * torso_size_multiplier, max_dist)

    def _get_pose_distance_embedding(self, landmarks):
        """构造姿态特征：多对关键点间的向量差"""
        embedding = np.array([
            self._get_distance(
                self._get_average_by_names(landmarks, 'left_hip', 'right_hip'),
                self._get_average_by_names(landmarks, 'left_shoulder', 'right_shoulder')),
            self._get_distance_by_names(landmarks, 'left_shoulder', 'left_elbow'),
            self._get_distance_by_names(landmarks, 'right_shoulder', 'right_elbow'),
            self._get_distance_by_names(landmarks, 'left_elbow', 'left_wrist'),
            self._get_distance_by_names(landmarks, 'right_elbow', 'right_wrist'),
            self._get_distance_by_names(landmarks, 'left_hip', 'left_knee'),
            self._get_distance_by_names(landmarks, 'right_hip', 'right_knee'),
            self._get_distance_by_names(landmarks, 'left_knee', 'left_ankle'),
            self._get_distance_by_names(landmarks, 'right_knee', 'right_ankle'),
            self._get_distance_by_names(landmarks, 'left_shoulder', 'left_wrist'),
            self._get_distance_by_names(landmarks, 'right_shoulder', 'right_wrist'),
            self._get_distance_by_names(landmarks, 'left_hip', 'left_ankle'),
            self._get_distance_by_names(landmarks, 'right_hip', 'right_ankle'),
            self._get_distance_by_names(landmarks, 'left_hip', 'left_wrist'),
            self._get_distance_by_names(landmarks, 'right_hip', 'right_wrist'),
            self._get_distance_by_names(landmarks, 'left_shoulder', 'left_ankle'),
            self._get_distance_by_names(landmarks, 'right_shoulder', 'right_ankle'),
            self._get_distance_by_names(landmarks, 'left_elbow', 'right_elbow'),
            self._get_distance_by_names(landmarks, 'left_knee', 'right_knee'),
            self._get_distance_by_names(landmarks, 'left_wrist', 'right_wrist'),
            self._get_distance_by_names(landmarks, 'left_ankle', 'right_ankle'),
        ])
        return embedding

    def _get_average_by_names(self, landmarks, name_from, name_to):
        lmk_from = landmarks[self._landmark_names.index(name_from)]
        lmk_to = landmarks[self._landmark_names.index(name_to)]
        return (lmk_from + lmk_to) * 0.5

    def _get_distance_by_names(self, landmarks, name_from, name_to):
        lmk_from = landmarks[self._landmark_names.index(name_from)]
        lmk_to = landmarks[self._landmark_names.index(name_to)]
        return self._get_distance(lmk_from, lmk_to)

    def _get_distance(self, lmk_from, lmk_to):
        return lmk_to - lmk_from

class PoseClassifier(object):
    """姿态分类器：根据嵌入向量与样本库比对分类"""
    def __init__(self, pose_samples_folder, pose_embedder,
                 file_extension='csv', file_separator=',',
                 n_landmarks=33, n_dimensions=3,
                 top_n_by_max_distance=30, top_n_by_mean_distance=10,
                 axes_weights=(1., 1., 0.2)):
        self._pose_embedder = pose_embedder
        self._n_landmarks = n_landmarks
        self._n_dimensions = n_dimensions
        self._top_n_by_max_distance = top_n_by_max_distance
        self._top_n_by_mean_distance = top_n_by_mean_distance
        self._axes_weights = axes_weights
        self._pose_samples = self._load_pose_samples(pose_samples_folder,
                                                     file_extension,
                                                     file_separator,
                                                     n_landmarks,
                                                     n_dimensions,
                                                     pose_embedder)

    def _load_pose_samples(self, folder, extension, separator, n_landmarks, n_dimensions, embedder):
        """从CSV文件加载姿态样本"""
        file_names = [name for name in os.listdir(folder) if name.endswith(extension)]
        pose_samples = []
        for file_name in file_names:
            class_name = file_name[:-(len(extension) + 1)]
            with open(os.path.join(folder, file_name)) as csv_file:
                csv_reader = csv.reader(csv_file, delimiter=separator)
                for row in csv_reader:
                    assert len(row) == n_landmarks * n_dimensions + 1
                    landmarks = np.array(row[1:], np.float32).reshape([n_landmarks, n_dimensions])
                    pose_samples.append(PoseSample(
                        name=row[0],
                        landmarks=landmarks,
                        class_name=class_name,
                        embedding=embedder(landmarks),
                    ))
        return pose_samples

    def find_pose_sample_outliers(self):
        """检测样本集中标注错误的异常样本"""
        outliers = []
        for sample in self._pose_samples:
            result = self.__call__(sample.landmarks)
            best_matches = [name for name, count in result.items()
                            if count == max(result.values())]
            if sample.class_name not in best_matches or len(best_matches) != 1:
                outliers.append(PoseSampleOutlier(sample, best_matches, result))
        return outliers

    def __call__(self, pose_landmarks):
        """分类输入姿态，返回各类别的匹配数量"""
        assert pose_landmarks.shape == (self._n_landmarks, self._n_dimensions)
        embedding = self._pose_embedder(pose_landmarks)
        flipped_embedding = self._pose_embedder(pose_landmarks * np.array([-1, 1, 1]))

        # 过滤异常方向（最大距离筛选）
        max_dist_heap = []
        for idx, sample in enumerate(self._pose_samples):
            max_dist = min(
                np.max(np.abs(sample.embedding - embedding) * self._axes_weights),
                np.max(np.abs(sample.embedding - flipped_embedding) * self._axes_weights),
            )
            max_dist_heap.append([max_dist, idx])
        max_dist_heap = sorted(max_dist_heap, key=lambda x: x[0])[:self._top_n_by_max_distance]

        # 平均距离筛选
        mean_dist_heap = []
        for _, idx in max_dist_heap:
            sample = self._pose_samples[idx]
            mean_dist = min(
                np.mean(np.abs(sample.embedding - embedding) * self._axes_weights),
                np.mean(np.abs(sample.embedding - flipped_embedding) * self._axes_weights),
            )
            mean_dist_heap.append([mean_dist, idx])
        mean_dist_heap = sorted(mean_dist_heap, key=lambda x: x[0])[:self._top_n_by_mean_distance]

        # 分类计数
        class_names = [self._pose_samples[idx].class_name for _, idx in mean_dist_heap]
        return {name: class_names.count(name) for name in set(class_names)}

if __name__ == "__main__":
    def test_embedder():
        fake_landmarks = np.random.rand(33, 3).astype(np.float32) * 100
        embedder = BodyPoseEmbedder()
        embedding = embedder(fake_landmarks)
        print("嵌入向量形状:", embedding.shape)
        print("部分嵌入值:", embedding[:3])
    test_embedder()
    def test_classifier():
        embedder = BodyPoseEmbedder()
        classifier = PoseClassifier(
            pose_samples_folder='pose_samples',
            pose_embedder=embedder,
            top_n_by_max_distance=5,
            top_n_by_mean_distance=3
        )
        fake_landmarks = np.random.rand(33, 3).astype(np.float32) * 100
        result = classifier(fake_landmarks)
        print("分类结果:", result)
    test_classifier()