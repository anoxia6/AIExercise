import csv
import random
from datetime import datetime, timedelta

# 定义日期范围
start_date = datetime(2025, 6, 28)
end_date = datetime(2025, 7, 7)

# 运动类型列表
exercise_types = ['深蹲', '仰卧起坐', '俯卧撑']

# 生成日期范围内的所有日期
current_date = start_date
dates = []
while current_date <= end_date:
    dates.append(current_date.strftime('%Y-%m-%d'))
    current_date += timedelta(days=1)

# 准备数据
all_records = []

for date in dates:
    # 每天生成4-7条记录
    records_per_day = random.randint(4, 7)
    
    for _ in range(records_per_day):
        # 随机选择运动类型
        exercise_type = random.choice(exercise_types)
        
        # 生成count：90%小于50，且整体80%为5的倍数
        if random.random() < 0.9:  # 90%的概率count小于50（范围10-49）
            if random.random() < 0.8:  # 其中80%为5的倍数
                base = random.randint(2, 9)  # 5×2=10，5×9=45
                count = 5 * base
            else:  # 20%为非5的倍数
                while True:
                    count = random.randint(10, 49)
                    if count % 5 != 0:
                        break
        else:  # 10%的概率count≥50（范围50-100）
            if random.random() < 0.8:  # 其中80%为5的倍数
                base = random.randint(10, 20)  # 5×10=50，5×20=100
                count = 5 * base
            else:  # 20%为非5的倍数
                while True:
                    count = random.randint(50, 100)
                    if count % 5 != 0:
                        break
        
        # 随机生成评分(78-91)
        score = random.randint(78, 91)
        
        # 添加到记录列表
        all_records.append({
            'date': date,
            'type': exercise_type,
            'count': count,
            'score': score
        })

# 写入CSV文件
csv_filename = 'exercise_records.csv'
with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['date', 'type', 'count', 'score']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    
    # 写入表头
    writer.writeheader()
    # 写入所有记录
    writer.writerows(all_records)

print(f"CSV文件已生成: {csv_filename}")
print(f"共生成 {len(all_records)} 条记录")