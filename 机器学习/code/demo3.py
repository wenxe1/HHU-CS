# 导入必要的库
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
import time

# ---------------------- 1. 数据加载与预处理 ----------------------
# 加载Iris数据集
iris = load_iris()
X = iris.data  # 特征：花萼长度、花萼宽度、花瓣长度、花瓣宽度
y = iris.target  # 标签：0=山鸢尾，1=变色鸢尾，2=维吉尼亚鸢尾

# 划分训练集和测试集（测试集占30%，stratify保证类别分布均衡）
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y
)

# 特征标准化（仅针对kNN和逻辑回归）
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# ---------------------- 2. 定义模型 ----------------------
models = {
    'kNN (k=5)': KNeighborsClassifier(n_neighbors=5),  # 经典k=5的kNN
    '朴素贝叶斯': GaussianNB(),  # 高斯朴素贝叶斯（适配连续特征）
    '逻辑回归': LogisticRegression(max_iter=200, random_state=42)  # 增加迭代次数确保收敛
}

# ---------------------- 3. 训练模型并记录结果 ----------------------
results = {
    '算法': [],
    '准确率': [],
    '运行时间(ms)': []
}

for name, model in models.items():
    # 记录开始时间
    start_time = time.time()
    
    # 区分是否使用标准化数据（朴素贝叶斯无需标准化）
    if name == '朴素贝叶斯':
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
    else:
        model.fit(X_train_scaled, y_train)
        y_pred = model.predict(X_test_scaled)
    
    # 记录结束时间并计算耗时（转换为毫秒）
    run_time = (time.time() - start_time) * 1000
    # 计算分类准确率
    accuracy = accuracy_score(y_test, y_pred)
    
    # 保存结果
    results['算法'].append(name)
    results['准确率'].append(accuracy)
    results['运行时间(ms)'].append(run_time)

# 转换为DataFrame便于查看
results_df = pd.DataFrame(results)
print("三种算法的性能指标：")
print(results_df.round(4))

# ---------------------- 4. 可视化对比 ----------------------
# 设置中文字体（避免乱码）
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 创建1行2列的子图
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# 子图1：准确率对比
sns.barplot(x='算法', y='准确率', data=results_df, ax=ax1, palette='Set2')
ax1.set_title('三种算法的分类准确率对比', fontsize=12)
ax1.set_ylim(0.9, 1.0)  # 缩小y轴范围，突出差异
ax1.set_ylabel('准确率')
# 添加数值标签
for i, v in enumerate(results_df['准确率']):
    ax1.text(i, v + 0.002, f'{v:.4f}', ha='center', fontsize=10)

# 子图2：运行时间对比
sns.barplot(x='算法', y='运行时间(ms)', data=results_df, ax=ax2, palette='Set3')
ax2.set_title('三种算法的运行时间对比（训练+预测）', fontsize=12)
ax2.set_ylabel('运行时间 (毫秒)')
# 添加数值标签
for i, v in enumerate(results_df['运行时间(ms)']):
    ax2.text(i, v + 0.05, f'{v:.2f}', ha='center', fontsize=10)

# 调整布局并显示图表
plt.tight_layout()
plt.show()