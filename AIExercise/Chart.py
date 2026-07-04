import csv
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from Ui_MyData import Ui_MyData
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTime, pyqtSignal
from PyQt5.QtWidgets import QDialog, QDialogButtonBox

class MyDataDialog(QDialog):
    """我的数据对话框类"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MyData()
        self.ui.setupUi(self)
        
        self.chart_manager = chartManager()
        ########### 生成运动计划 ###########
        '''权重打分为[0.3, 0.35, 0.4]，即深蹲的count*0.3，仰卧起坐的count*0.35，俯卧撑的count*0.4
        比较三者的大小
        1. 深蹲：count*0.3
        2. 仰卧起坐：count*0.35
        3. 俯卧撑：count*0.4
        对于加权后最大的运动类型，明天运动量为[20, 30]
        对于加权后最小的运动类型，明天运动量为[50, 70]
        对于加权后中间的运动类型，明天运动量为[30, 50]
        计划量只能是5的倍数'''
        actcount_data = self.chart_manager.get_actcount_data()
        squat_count = sum(data[0] for data in actcount_data) * 0.3
        situp_count = sum(data[1] for data in actcount_data) * 0.35
        pushup_count = sum(data[2] for data in actcount_data) * 0.4
        
        counts = [squat_count, situp_count, pushup_count]
        max_index = np.argmax(counts)
        min_index = np.argmin(counts)
        mid_index = 3 - max_index - min_index
        
        plan_counts = [0, 0, 0]
        plan_counts[max_index] = np.random.choice([20, 30])
        plan_counts[min_index] = np.random.choice([50, 60])
        plan_counts[mid_index] = np.random.choice([30, 40])
        
        plan_counts = [int(np.ceil(count / 5) * 5) for count in plan_counts]
        self.ui.sdlcdNumber.display(plan_counts[2])
        self.ui.ywqzlcdNumber.display(plan_counts[1])
        self.ui.fwclcdNumber.display(plan_counts[0])
        
        self.ui.exitpushButton.clicked.connect(self.on_exit_clicked)
        self.ui.actfrepushButton.clicked.connect(self.on_frequency_clicked)
        self.ui.scorepushButton.clicked.connect(self.on_score_clicked)
        self.ui.heatpushButton.clicked.connect(self.on_calories_clicked)
        self.ui.timepartpushButton.clicked.connect(self.on_time_proportion_clicked)
        
        self.ui.graphlabel.setText("请选择要查看的图表")
        
    def on_exit_clicked(self):
        """退出按钮点击时的处理"""
        print("退出按钮被点击")
        self.accept()
        self.close()
        
    def on_frequency_clicked(self):
        """频率按钮点击时的处理"""
        print("频率按钮被点击")
        self.chart_manager.point_frequency_line_chart()
        chart = QImage('temp.png')
        self.ui.graphlabel.setPixmap(QPixmap.fromImage(chart))
        
    def on_score_clicked(self):
        """评分按钮点击时的处理"""
        print("评分按钮被点击")
        self.chart_manager.point_score_line_chart()
        chart = QImage('temp.png')
        self.ui.graphlabel.setPixmap(QPixmap.fromImage(chart))
    
    def on_calories_clicked(self):
        """卡路里按钮点击时的处理"""
        print("卡路里按钮被点击")
        self.chart_manager.point_calories_line_chart()
        chart = QImage('temp.png')
        self.ui.graphlabel.setPixmap(QPixmap.fromImage(chart))

        
    def on_time_proportion_clicked(self):
        """时间占比按钮点击时的处理"""
        print("时间占比按钮被点击")
        self.chart_manager.point_time_proportion_pie_chart()
        chart = QImage('temp.png')
        self.ui.graphlabel.setPixmap(QPixmap.fromImage(chart))

class chartManager:
    """图表管理类"""
    def __init__(self):
        self.csv_manager = csvManager('exercise_records.csv')
        self.data_list = self.csv_manager.read_csv()
        plt.rcParams['font.size'] = 2.4  # 设置字体大小
    
    def get_actfrequency_data(self):
        """获取活动频率数据,返回一个二维数组，每行代表一天内三种运动的频率数据"""
        # 初始化日期映射表（日期字符串 -> 索引）
        date_index_map = {}
        actfrequency_data = []
        
        # 收集所有日期并排序
        all_dates = sorted({record['date'] for record in self.data_list if 'date' in record})
        
        # 为每个日期分配索引，并初始化数据行
        for idx, date in enumerate(all_dates):
            date_index_map[date] = idx
            actfrequency_data.append([0, 0, 0])  # 深蹲、仰卧起坐、俯卧撑
        
        # 处理每条记录
        for record in self.data_list:
            if 'date' in record and 'type' in record:
                date = record['date']
                act_type = record['type']
                
                # 检查日期是否在映射表中
                if date in date_index_map:
                    idx = date_index_map[date]
                    # 根据运动类型更新频率数据
                    if act_type == '深蹲':  
                        actfrequency_data[idx][0] += 1
                    elif act_type == '仰卧起坐':    
                        actfrequency_data[idx][1] += 1
                    elif act_type == '俯卧撑':
                        actfrequency_data[idx][2] += 1
        
        # 处理最近7天的数据
        if all_dates:
            # 获取最近7天的日期（假设日期已排序）
            recent_7_dates = all_dates[-7:] if len(all_dates) > 7 else all_dates
            # 提取对应的数据
            recent_data = [actfrequency_data[date_index_map[date]] for date in recent_7_dates]
            # 补全不足7天的数据
            while len(recent_data) < 7:
                recent_data.append([0, 0, 0])
            return recent_data
        return [[0, 0, 0]] * 7  # 无数据时返回7天全0


    def get_actcount_data(self):
        """获取活动计数数据,返回一个二维数组，每行代表一天内三种运动的总计数数据"""
        date_index_map = {}
        actcount_data = []
        
        all_dates = sorted({record['date'] for record in self.data_list if 'date' in record})
        
        for idx, date in enumerate(all_dates):
            date_index_map[date] = idx
            actcount_data.append([0, 0, 0])  # 深蹲、仰卧起坐、俯卧撑
        
        for record in self.data_list:
            if 'date' in record and 'type' in record and 'count' in record:
                date = record['date']
                act_type = record['type']
                count = int(record['count'])  # 确保转换为整数
                
                if date in date_index_map:
                    idx = date_index_map[date]
                    if act_type == '深蹲':  
                        actcount_data[idx][0] += count
                    elif act_type == '仰卧起坐':    
                        actcount_data[idx][1] += count
                    elif act_type == '俯卧撑':
                        actcount_data[idx][2] += count
        
        if all_dates:
            recent_7_dates = all_dates[-7:] if len(all_dates) > 7 else all_dates
            recent_data = [actcount_data[date_index_map[date]] for date in recent_7_dates]
            while len(recent_data) < 7:
                recent_data.append([0, 0, 0])
            return recent_data
        return [[0, 0, 0]] * 7


    def get_actscore_data(self):
        """获取活动评分数据,返回一个二维数组，每行代表一天内三种运动的平均评分数据"""
        date_index_map = {}
        actscore_data = []
        actcount_data = []  # 用于记录每种运动的次数
        
        all_dates = sorted({record['date'] for record in self.data_list if 'date' in record})
        
        for idx, date in enumerate(all_dates):
            date_index_map[date] = idx
            actscore_data.append([0, 0, 0])     # 总分
            actcount_data.append([0, 0, 0])     # 次数
        
        for record in self.data_list:
            if 'date' in record and 'type' in record and 'score' in record:
                date = record['date']
                act_type = record['type']
                score = int(record['score'])     # 确保转换为整数
                
                if date in date_index_map:
                    idx = date_index_map[date]
                    if act_type == '深蹲':  
                        actscore_data[idx][0] += score
                        actcount_data[idx][0] += 1
                    elif act_type == '仰卧起坐':    
                        actscore_data[idx][1] += score
                        actcount_data[idx][1] += 1
                    elif act_type == '俯卧撑':
                        actscore_data[idx][2] += score
                        actcount_data[idx][2] += 1
        
        # 计算平均评分
        for i in range(len(actscore_data)):
            for j in range(3):
                if actcount_data[i][j] > 0:
                    actscore_data[i][j] /= actcount_data[i][j]
                else:
                    actscore_data[i][j] = 60.0
        
        if all_dates:
            recent_7_dates = all_dates[-7:] if len(all_dates) > 7 else all_dates
            recent_data = [actscore_data[date_index_map[date]] for date in recent_7_dates]
            while len(recent_data) < 7:
                recent_data.append([0.0, 0.0, 0.0])
            return recent_data
        return [[0.0, 0.0, 0.0]] * 7

    def get_acttime_proportion(self):
        """获取活动时间占比数据,返回一个二维数组，每行代表一天内三种运动的时间占比数据"""
        date_index_map = {}
        acttime_data = []
        
        all_dates = sorted({record['date'] for record in self.data_list if 'date' in record})
        
        for idx, date in enumerate(all_dates):
            date_index_map[date] = idx
            acttime_data.append([0, 0, 0])  # 深蹲、仰卧起坐、俯卧撑的计数
        
        for record in self.data_list:
            if 'date' in record and 'type' in record and 'count' in record:
                date = record['date']
                act_type = record['type']
                count = int(record['count'])  # 确保转换为整数
                
                if date in date_index_map:
                    idx = date_index_map[date]
                    if act_type == '深蹲':  
                        acttime_data[idx][0] += count
                    elif act_type == '仰卧起坐':    
                        acttime_data[idx][1] += count
                    elif act_type == '俯卧撑':
                        acttime_data[idx][2] += count
        
        # 计算时间占比
        for i in range(len(acttime_data)):
            total_time = sum(acttime_data[i])
            if total_time > 0:
                acttime_data[i] = [time / total_time for time in acttime_data[i]]
            else:
                acttime_data[i] = [0.0, 0.0, 0.0]
        
        if all_dates:
            recent_7_dates = all_dates[-7:] if len(all_dates) > 7 else all_dates
            recent_data = [acttime_data[date_index_map[date]] for date in recent_7_dates]
            while len(recent_data) < 7:
                recent_data.append([0.0, 0.0, 0.0])
            return recent_data
        return [[0.0, 0.0, 0.0]] * 7
    
    def point_frequency_line_chart(self):
        """绘制点频率折线图，保存为temp.png，不显示图表"""
        ##################  图表格式  ##################
        # 1. x轴表示日期
        # 2. y轴表示频率
        # 3. 每个点代表一天内某种运动的频率
        # 4. 折线图显示一周内三种运动的频率变化趋势,三条线分别代表深蹲、仰卧起坐和俯卧撑
        # 5. 图表标题为"exercise frequency"
        # 6. 图例显示三种运动的名称
        # 7. x轴标签为"data"，y轴标签为"frequency"
        # 8. 图表大小像素为640x380
        ##################################################
        actfrequency_data = self.get_actfrequency_data()
        dates = [i for i in range(len(actfrequency_data))]
        squat_freq = [data[0] for data in actfrequency_data]
        situp_freq = [data[1] for data in actfrequency_data]
        pushup_freq = [data[2] for data in actfrequency_data]
        plt.figure(figsize=(2.133, 1.266))
        plt.plot(dates, squat_freq, label='squat', marker='o', markersize=3)
        plt.plot(dates, situp_freq, label='situp', marker='o', markersize=3)
        plt.plot(dates, pushup_freq, label='pushup', marker='o', markersize=3)
        plt.title('exercise frequency')
        plt.xlabel('date')
        plt.ylabel('frequency')
        plt.xlim(0, 6)  # 限制x轴范围为0到6
        plt.legend()
        plt.grid(True)
        plt.xticks(dates)
        plt.tight_layout()
        plt.savefig('temp.png', bbox_inches='tight', dpi=300)
    
    def point_score_line_chart(self):
        """绘制点评分折线图，保存为temp.png，不显示图表"""
        ##################  图表格式  ##################
        # 1. x轴表示日期
        # 2. y轴表示评分
        # 3. 每个点代表一天内某种运动的平均评分
        # 4. 折线图显示一周内三种运动的评分变化趋势,三条线分别代表深蹲、仰卧起坐和俯卧撑
        # 5. 图表标题为"exercise score"
        # 6. 图例显示三种运动的英文名称
        # 7. x轴标签为"date"，y轴标签为"score"
        # 8. 图表大小像素为640x380
        ##################################################
        actscore_data = self.get_actscore_data()
        dates = [i for i in range(len(actscore_data))]
        squat_scores = [data[0] for data in actscore_data]
        situp_scores = [data[1] for data in actscore_data]
        pushup_scores = [data[2] for data in actscore_data]
        plt.figure(figsize=(2.133, 1.266))
        plt.plot(dates, squat_scores, label='squat', marker='o', markersize=2)
        plt.plot(dates, situp_scores, label='situp', marker='o', markersize=2)
        plt.plot(dates, pushup_scores, label='pushup', marker='o', markersize=2)
        plt.title('exercise score')
        plt.xlabel('date')
        plt.ylabel('score')
        plt.xlim(0, 6)  # 限制x轴范围为0到6
        plt.ylim(60, 100)  # 限制y轴范围为
        plt.legend()
        plt.grid(True)
        plt.xticks(dates)
        plt.tight_layout()
        plt.savefig('temp.png', bbox_inches='tight', dpi=300)
    
    def point_calories_line_chart(self):
        """绘制点卡路里分布热力图，保存为temp.png，不显示图表"""
        """卡路里计算公式：
        深蹲：每次消耗0.2-0.5卡路里
        仰卧起坐：每次消耗0.3-0.8卡路里
        俯卧撑：每次消耗0.5-1卡路里"""
        ##################  图表格式  ##################
        # 1. 表格为3行7列，行表示三种运动，列表示一周内的每天
        # 2. 每个单元格表示该运动在该天的卡路里消耗
        # 3. 使用热力图显示卡路里分布，颜色深浅表示卡路里消耗的多少
        # 4. 图表标题为"exercise calories distribution"
        # 5. x轴标签为"date"，y轴标签为"exercise type"
        # 6. 图表大小像素为640x380
        ##################################################
        actfrequency_data = self.get_actfrequency_data()
        squat_calories = [data[0] * np.random.uniform(0.2, 0.5) for data in actfrequency_data]
        situp_calories = [data[1] * np.random.uniform(0.3, 0.8) for data in actfrequency_data]
        pushup_calories = [data[2] * np.random.uniform(0.5, 1.0) for data in actfrequency_data]
        calories_data = [squat_calories, situp_calories, pushup_calories]
        dates = [i for i in range(len(calories_data[0]))]
        plt.figure(figsize=(2.133, 1.266))
        sns.heatmap(calories_data, annot=True, fmt=".1f", cmap='YlGnBu', xticklabels=dates, yticklabels=['squat', 'sit up', 'push up'])
        plt.title('exercise calories distribution')
        plt.xlabel('date')
        plt.ylabel('exercise type')
        plt.tight_layout()
        plt.savefig('temp.png', bbox_inches='tight', dpi=300)
    
    def point_time_proportion_pie_chart(self):
        """绘制点时间占比饼图，时间以次数记，视为三种运动每次花费时间一样，保存为temp.png，不显示图表，无返回"""
        ###################  图表格式  ##################
        # 1. 总图表有八个子图，前七个子饼图显示三种运动在一天内的时间占比，最后一个子图显示三种运动的总时间占比
        # 2. 每个子饼图的标题为"date: YYYY-MM-DD"，表示该饼图对应的日期
        # 3. 每个子饼图的标签为三种运动的英文名称
        # 4. 每个子饼图的颜色分别为深蹲（蓝色）、仰卧起坐（橙色）、俯卧撑（绿色）
        # 5. 总图表的像素大小为640x380
        # 6. 每个子饼图的大小为2x2英寸
        ##################################################
        acttime_data = self.get_acttime_proportion()
        dates = [i for i in range(len(acttime_data))]
        squat_time = [data[0] for data in acttime_data]
        situp_time = [data[1] for data in acttime_data]
        pushup_time = [data[2] for data in acttime_data]
        total_time = [sum(data) for data in acttime_data]
        fig, axs = plt.subplots(2, 4, figsize=(2.133, 1.266))
        axs = axs.flatten()
        for i in range(len(dates)):
            axs[i].pie([squat_time[i], situp_time[i], pushup_time[i]], 
                       labels=['squat', 'situp', 'pushup'], 
                       colors=['blue', 'orange', 'green'], 
                       autopct='%1.1f%%')
            axs[i].set_title(f'date: {dates[i]}')
        # 最后一个子图显示总时间占比
        axs[-1].pie([sum(squat_time), sum(situp_time), sum(pushup_time)],
                    labels=['squat', 'situp', 'pushup'], 
                    colors=['blue', 'orange', 'green'], 
                    autopct='%1.1f%%')
        axs[-1].set_title('Total time proportion')
        plt.tight_layout()
        # 保存图表为temp.png
        plt.savefig('temp.png', bbox_inches='tight', dpi=300)
        
class csvManager:
    """CSV文件管理类"""
    def __init__(self, filename):
        self.filename = 'exercise_records.csv' if filename is None else filename
    
    def read_csv(self):
        """使用pandas读取CSV文件，并返回数据列表，每行数据为一个字典"""
        #################  csv文件格式  ##################
        # 1. 每一行代表一次运动记录
        # 2. 每一行包含多个字段，字段之间用逗号分隔
        # 3. 字段包括：运动时间（YYYY-MM-DD）、运动类型（深蹲、仰卧起坐、俯卧撑）、运动计数、评分（0-100）
        # 4. 例如：2023-10-01,深蹲,20,85
        # 5. 字典格式：{'date': '2023-10-01', 'type': '深蹲', 'count': 20, 'score': 85}
        ##################################################
        try:
            df = pd.read_csv(self.filename, encoding='utf-8')
            data_list = df.to_dict(orient='records')
            print(f"成功读取文件 {self.filename}，共 {len(data_list)} 条记录。")
            return data_list
        except FileNotFoundError:
            print(f"文件 {self.filename} 不存在，返回空列表。")
            return []
        except Exception as e:
            print(f"读取文件 {self.filename} 时发生错误: {e}")
            return []
    
    def write_to_csv(self, data):
        """写入数据到CSV文件，记录添加到文件末尾"""
        ##################  data格式  ##################
        # 1. data是一个字典，每个字典代表一条记录
        # 2. 字典格式：{'date': '2023-10-01', 'type': '深蹲', 'count': 20, 'score': 85}
        # 3. 每个字典的键必须与CSV文件的字段一致
        ##################################################
        try:
            with open(self.filename, 'a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                for record in data:
                    if 'date' in record and 'type' in record and 'count' in record and 'score' in record:
                        writer.writerow([record['date'], record['type'], record['count'], record['score']])
                        print(f"记录已写入文件 {self.filename}: {record}")
        except Exception as e:
            print(f"写入文件 {self.filename} 时发生错误: {e}")
        
    @staticmethod
    def clear_csv(self):
        """清空CSV文件内容"""
        try:
            with open(self.filename, 'w', encoding='utf-8') as file:
                file.truncate(0)  # 清空文件内容
                print(f"文件 {self.filename} 已清空。")
        except Exception as e:
            print(f"清空文件 {self.filename} 时发生错误: {e}")