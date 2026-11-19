# -*- coding: utf-8 -*-
"""
Iris 三算法对比：kNN、GaussianNB、LogisticRegression
评价指标：10 折交叉验证准确率 + 训练耗时
"""
import time, warnings, matplotlib.pyplot as plt
from sklearn.datasets import load_iris
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import LogisticRegression
import seaborn as sns
import pandas as pd

warnings.filterwarnings("ignore")
plt.rcParams['font.sans-serif'] = ['SimHei']   # 显示中文
plt.rcParams['axes.unicode_minus'] = False

# 1. 读取数据
X, y = load_iris(return_X_y=True)

# 2. 定义三种模型（用 Pipeline 统一做标准化）
models = {
    'kNN': Pipeline([('sc', StandardScaler()),
                     ('clf', KNeighborsClassifier(n_neighbors=5))]),
    'GaussianNB': Pipeline([('sc', StandardScaler()),
                            ('clf', GaussianNB())]),
    'LogisticRegression': Pipeline([('sc', StandardScaler()),
                                    ('clf', LogisticRegression(max_iter=200, multi_class='multinomial'))])
}

cv = StratifiedKFold(n_splits=10, shuffle=True, random_state=42)

# 3. 评估：准确率 + 耗时
results, times = [], []
for name, model in models.items():
    t0 = time.time()
    scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy')
    t1 = time.time()
    results.append(scores)
    times.append(t1 - t0)
    print(f"{name:18s} | 平均准确率: {scores.mean():.4f}±{scores.std():.4f} | 耗时: {times[-1]:.4f}s")

# 4. 可视化
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

# 4.1 准确率箱线图
df_score = pd.DataFrame({name: scores for name, scores in zip(models.keys(), results)})
sns.boxplot(data=df_score, ax=ax1, palette='Set2')
ax1.set_title('10 折交叉验证准确率分布')
ax1.set_ylabel('Accuracy')

# 4.2 训练耗时柱状图
ax2.bar(models.keys(), times, color=sns.color_palette('Set2'))
ax2.set_title('10 折交叉验证训练总耗时')
ax2.set_ylabel('Time / s')
for i, v in enumerate(times):
    ax2.text(i, v + 0.001, f'{v:.3f}', ha='center')

plt.tight_layout()
plt.show()