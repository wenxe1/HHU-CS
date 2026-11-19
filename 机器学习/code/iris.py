import sys
import time
import platform
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import font_manager
from sklearn import datasets
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

# --- 1. 解决控制台输出乱码 ---
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# --- 2. 核心修复：解决图表中文乱码 (方块问题) ---
# 关键步骤：先设置 Seaborn 主题
sns.set_theme(style="whitegrid", context="notebook")

# 关键步骤：再设置字体。这里按优先级尝试系统可能存在的字体
system_name = platform.system()
if system_name == 'Windows':
    # Windows 优先尝试 微软雅黑 -> 黑体 -> 宋体
    fonts = ['Microsoft YaHei', 'SimHei', 'SimSun', 'Arial']
elif system_name == 'Darwin':
    # Mac 优先尝试 Arial Unicode MS -> PingFang SC
    fonts = ['Arial Unicode MS', 'PingFang SC', 'Heiti TC']
else:
    # Linux
    fonts = ['WenQuanYi Micro Hei', 'Droid Sans Fallback']

# 将字体应用到 Matplotlib
plt.rcParams['font.sans-serif'] = fonts + plt.rcParams['font.sans-serif']
plt.rcParams['axes.unicode_minus'] = False # 解决负号显示为方块的问题
plt.rcParams['figure.dpi'] = 120 # 提高分辨率

# --- 3. 数据准备 ---
print("正在加载数据...")
iris = datasets.load_iris()
X = iris.data
y = iris.target

# 划分训练集和测试集
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 标准化 (这对 kNN 和 逻辑回归 很重要)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# --- 4. 训练与评估 ---
models = {
    "kNN (k=3)": KNeighborsClassifier(n_neighbors=3),
    "朴素贝叶斯": GaussianNB(),
    "逻辑回归": LogisticRegression(max_iter=200)
}

results = {
    "模型": [], 
    "准确率": [], 
    "训练耗时(ms)": [], 
    "预测耗时(ms)": []
}

print(f"\n{'='*40}")
print(f"{'模型名称':<12} | {'准确率':<8} | {'训练(ms)':<8} | {'预测(ms)':<8}")
print(f"{'-'*50}")

for name, model in models.items():
    # 训练
    start_train = time.time()
    model.fit(X_train_scaled, y_train)
    train_time = (time.time() - start_train) * 1000
    
    # 预测
    start_pred = time.time()
    y_pred = model.predict(X_test_scaled)
    predict_time = (time.time() - start_pred) * 1000
    
    acc = accuracy_score(y_test, y_pred)
    
    # 存入字典
    results["模型"].append(name)
    results["准确率"].append(acc)
    results["训练耗时(ms)"].append(train_time)
    results["预测耗时(ms)"].append(predict_time)
    
    print(f"{name:<14} | {acc:.4f}     | {train_time:.3f}      | {predict_time:.3f}")

print(f"{'='*40}\n")
df_results = pd.DataFrame(results)

# --- 5. 绘图：性能对比柱状图 ---
fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
fig.suptitle('三种算法在 Iris 数据集上的性能对比', fontsize=16, fontweight='bold')

# 辅助函数：绘制带数值标签的柱状图
def draw_bar(ax, x, y, title, color_palette, ylim=None):
    # hue=x 避免警告, legend=False 隐藏图例
    sns.barplot(x=x, y=y, data=df_results, ax=ax, hue=x, palette=color_palette, legend=False)
    ax.set_title(title, fontsize=13, pad=10)
    ax.set_xlabel("机器学习算法", fontsize=11)
    ax.set_ylabel(y if not ylim else "")
    
    if ylim:
        ax.set_ylim(ylim)
        
    # 添加数值标签
    for p in ax.patches:
        height = p.get_height()
        ax.text(p.get_x() + p.get_width()/2., height,
                f'{height:.3f}',
                ha="center", va="bottom", fontsize=10, fontweight='bold', color='black')

# 绘制三张子图
draw_bar(axes[0], "模型", "准确率", "准确率 (越高越好)", "viridis", ylim=(0.8, 1.05))
draw_bar(axes[1], "模型", "训练耗时(ms)", "训练耗时 (越快越好)", "rocket_r")
draw_bar(axes[2], "模型", "预测耗时(ms)", "预测耗时 (越快越好)", "mako_r")

plt.show()

# --- 6. 绘图：决策边界可视化 (前两个特征) ---
print("正在绘制决策边界图...")

# 仅取前两个特征重新训练
X_2d = X[:, :2] 
scaler_2d = StandardScaler()
X_2d_scaled = scaler_2d.fit_transform(X_2d)

# 创建网格
x_min, x_max = X_2d_scaled[:, 0].min() - 0.5, X_2d_scaled[:, 0].max() + 0.5
y_min, y_max = X_2d_scaled[:, 1].min() - 0.5, X_2d_scaled[:, 1].max() + 0.5
xx, yy = np.meshgrid(np.arange(x_min, x_max, 0.02), np.arange(y_min, y_max, 0.02))

# 绘图容器
fig2, axes2 = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
fig2.suptitle('不同算法的分类决策边界 (仅使用花萼长度与宽度)', fontsize=16, fontweight='bold')

# 自定义颜色 (背景浅色，散点深色)
from matplotlib.colors import ListedColormap
cm_bg = ListedColormap(['#FFAAAA', '#AAFFAA', '#AAAAFF']) # 浅红、浅绿、浅蓝
cm_pts = ListedColormap(['#FF0000', '#00FF00', '#0000FF']) # 深红、深绿、深蓝

# 重新训练并绘图
model_list = [KNeighborsClassifier(3), GaussianNB(), LogisticRegression()]
titles = ['kNN (k=3)', '朴素贝叶斯', '逻辑回归']

for clf, title, ax in zip(model_list, titles, axes2):
    clf.fit(X_2d_scaled, y) # 使用全部y
    
    # 预测网格点
    Z = clf.predict(np.c_[xx.ravel(), yy.ravel()])
    Z = Z.reshape(xx.shape)
    
    # 画背景色块
    ax.contourf(xx, yy, Z, cmap=cm_bg, alpha=0.3)
    
    # 画训练点
    scatter = ax.scatter(X_2d_scaled[:, 0], X_2d_scaled[:, 1], c=y, cmap=cm_pts, edgecolors='k', s=40)
    
    ax.set_title(title, fontsize=14)
    ax.set_xlabel('特征1：花萼长度 (标准化)', fontsize=10)
    ax.set_ylabel('特征2：花萼宽度 (标准化)', fontsize=10)
    ax.grid(False)

plt.show()