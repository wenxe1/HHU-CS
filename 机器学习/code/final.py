import sys
import time
import platform
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn import datasets
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.pipeline import Pipeline
from matplotlib.colors import ListedColormap

# --- 1. 环境配置与字体解决 (保留代码1的强健性) ---
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# 设置 Seaborn 主题
sns.set_theme(style="whitegrid", context="notebook")

# 字体设置：按优先级适配 Windows/Mac/Linux
system_name = platform.system()
if system_name == 'Windows':
    fonts = ['Microsoft YaHei', 'SimHei', 'SimSun', 'Arial']
elif system_name == 'Darwin':
    fonts = ['Arial Unicode MS', 'PingFang SC', 'Heiti TC']
else:
    fonts = ['WenQuanYi Micro Hei', 'Droid Sans Fallback']

plt.rcParams['font.sans-serif'] = fonts + plt.rcParams['font.sans-serif']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 120

# --- 2. 数据准备 ---
print("正在加载数据...")
iris = datasets.load_iris()
X = iris.data
y = iris.target

# [融入代码3]：使用 stratify=y 进行分层抽样，保证训练集/测试集类别比例一致
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# 标准化 (用于单次分割评估)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# --- 3. 模型定义 ---
# 基础模型参数 (融合代码3的 k=5 配置)
knn_params = {'n_neighbors': 5}
lr_params = {'max_iter': 200, 'multi_class': 'multinomial', 'random_state': 42}

# 定义用于单次评估的模型实例
models_single = {
    "kNN (k=5)": KNeighborsClassifier(**knn_params),
    "朴素贝叶斯": GaussianNB(),
    "逻辑回归": LogisticRegression(**lr_params)
}

# [融入代码2]：定义用于交叉验证的 Pipeline，防止数据泄露
models_cv = {
    "kNN (k=5)": Pipeline([('sc', StandardScaler()), ('clf', KNeighborsClassifier(**knn_params))]),
    "朴素贝叶斯": Pipeline([('sc', StandardScaler()), ('clf', GaussianNB())]),
    "逻辑回归": Pipeline([('sc', StandardScaler()), ('clf', LogisticRegression(**lr_params))])
}

# --- 4. 训练与评估 ---

# 4.1 单次分割评估 (代码1逻辑：细分训练与预测时间)
results_single = {
    "模型": [], "准确率": [], "训练耗时(ms)": [], "预测耗时(ms)": []
}

print(f"\n{'='*60}")
print(f"{'模型名称':<12} | {'准确率':<8} | {'训练(ms)':<8} | {'预测(ms)':<8} | {'CV均值':<8}")
print(f"{'-'*70}")

for name, model in models_single.items():
    # 训练
    start_train = time.time()
    model.fit(X_train_scaled, y_train)
    train_time = (time.time() - start_train) * 1000
    
    # 预测
    start_pred = time.time()
    y_pred = model.predict(X_test_scaled)
    predict_time = (time.time() - start_pred) * 1000
    
    acc = accuracy_score(y_test, y_pred)
    
    results_single["模型"].append(name)
    results_single["准确率"].append(acc)
    results_single["训练耗时(ms)"].append(train_time)
    results_single["预测耗时(ms)"].append(predict_time)

# 4.2 交叉验证评估 (代码2逻辑：10折交叉验证 + 箱线图数据)
cv_scores_dict = {} # 存储每一折的分数用于画箱线图
cv_results_summary = []

cv = StratifiedKFold(n_splits=10, shuffle=True, random_state=42)

for name, pipeline in models_cv.items():
    # 执行交叉验证
    scores = cross_val_score(pipeline, X, y, cv=cv, scoring='accuracy')
    cv_scores_dict[name] = scores
    
    # 获取单次评估的结果以便打印在一起
    idx = results_single["模型"].index(name)
    single_acc = results_single["准确率"][idx]
    t_train = results_single["训练耗时(ms)"][idx]
    t_pred = results_single["预测耗时(ms)"][idx]
    
    print(f"{name:<14} | {single_acc:.4f}     | {t_train:.3f}      | {t_pred:.3f}      | {scores.mean():.4f}")

print(f"{'='*60}\n")
df_single = pd.DataFrame(results_single)
df_cv = pd.DataFrame(cv_scores_dict)

# --- 5. 综合绘图：性能与时间分析 ---
fig, axes = plt.subplots(1, 3, figsize=(18, 6), constrained_layout=True)
fig.suptitle('三种算法综合性能评估 (Iris数据集)', fontsize=18, fontweight='bold')

# 子图1：单次测试集准确率 (柱状图) - 代码1风格
sns.barplot(x="模型", y="准确率", data=df_single, ax=axes[0], palette="viridis", hue="模型", legend=False)
axes[0].set_title("测试集准确率 (单次分割)", fontsize=14)
axes[0].set_ylim(0.85, 1.05)
for p in axes[0].patches:
    axes[0].text(p.get_x() + p.get_width()/2., p.get_height(), f'{p.get_height():.3f}', 
                 ha="center", va="bottom", fontweight='bold')

# 子图2：交叉验证准确率分布 (箱线图) - 代码2风格
# 将数据转换为长格式以便 Seaborn 绘图
df_cv_melt = df_cv.melt(var_name='模型', value_name='准确率')
sns.boxplot(x='模型', y='准确率', data=df_cv_melt, ax=axes[1], palette="Set2", hue="模型", legend=False)
sns.swarmplot(x='模型', y='准确率', data=df_cv_melt, ax=axes[1], color=".25", size=4) # 添加散点显示分布
axes[1].set_title("10折交叉验证准确率分布 (稳定性)", fontsize=14)
axes[1].set_ylabel("准确率")

# 子图3：时间消耗对比 (堆叠图或分组柱状图)
# 整理时间数据
df_time = df_single.melt(id_vars="模型", value_vars=["训练耗时(ms)", "预测耗时(ms)"], var_name="阶段", value_name="耗时")
sns.barplot(x="模型", y="耗时", hue="阶段", data=df_time, ax=axes[2], palette="rocket")
axes[2].set_title("训练与预测耗时对比", fontsize=14)
axes[2].set_ylabel("时间 (ms)")

plt.show()

# --- 6. 绘图：决策边界可视化 (保留代码1的优秀可视化) ---
print("正在绘制决策边界图...")

# 仅取前两个特征重新训练 (花萼长度 vs 花萼宽度)
X_2d = X[:, :2]
y_2d = y

# 创建网格
x_min, x_max = X_2d[:, 0].min() - 0.5, X_2d[:, 0].max() + 0.5
y_min, y_max = X_2d[:, 1].min() - 0.5, X_2d[:, 1].max() + 0.5
xx, yy = np.meshgrid(np.arange(x_min, x_max, 0.02), np.arange(y_min, y_max, 0.02))

# 绘图容器
fig2, axes2 = plt.subplots(1, 3, figsize=(16, 5), constrained_layout=True)
fig2.suptitle('不同算法的分类决策边界 (仅使用花萼长度与宽度)', fontsize=16, fontweight='bold')

# 颜色定义
cm_bg = ListedColormap(['#FFAAAA', '#AAFFAA', '#AAAAFF'])
cm_pts = ListedColormap(['#FF0000', '#00FF00', '#0000FF'])

# 定义用于可视化的 Pipeline (需要在这里单独训练 2D 模型)
viz_models = [
    ("kNN (k=5)", Pipeline([('sc', StandardScaler()), ('clf', KNeighborsClassifier(n_neighbors=5))])),
    ("朴素贝叶斯", Pipeline([('sc', StandardScaler()), ('clf', GaussianNB())])),
    ("逻辑回归", Pipeline([('sc', StandardScaler()), ('clf', LogisticRegression(**lr_params))]))
]

for (name, model), ax in zip(viz_models, axes2):
    # 在 2D 数据上训练
    model.fit(X_2d, y_2d)
    
    # 预测网格点
    Z = model.predict(np.c_[xx.ravel(), yy.ravel()])
    Z = Z.reshape(xx.shape)
    
    # 画背景色块
    ax.contourf(xx, yy, Z, cmap=cm_bg, alpha=0.3)
    
    # 画训练点
    scatter = ax.scatter(X_2d[:, 0], X_2d[:, 1], c=y_2d, cmap=cm_pts, edgecolors='k', s=40)
    
    ax.set_title(name, fontsize=14)
    ax.set_xlabel('花萼长度 (cm)', fontsize=11)
    ax.set_ylabel('花萼宽度 (cm)', fontsize=11)

plt.show()