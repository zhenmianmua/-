# -*- coding: utf-8 -*-
"""
基于遗传算法的探索收益优化

Created on 2025.10.23

作者: 暮山紫

邀请码(欢迎加好友): 11121248

github主页(欢迎关注): https://github.com/zhenmianmua
"""
import random
from tqdm import tqdm
# 问题描述与算法原理：
'''
我拥有至多19个伙伴，每个伙伴都有不同的战力，需要安排这些伙伴探索不同的关卡；
关卡最多22个，每个关卡都有不同的战力需求和资源收获，且每个关卡最多安排4名伙伴，最少可以安排0人；
如果对应关卡被安排的伙伴战力之和大于等于其战力需求，则完整获得关卡对应资源数，
否则获得的资源要乘上（实际战力/需求战力）系数。
我想让获取的总资源最多。
理论上，这个问题是存在最优解的，表示为数组x0=[a,b,c,……]，其中的每个元素都是对应伙伴的分配策略
但由于选择过多，用遍历的方法求最优解难以实现，因此选择遗传算法求次优解。
每个“个体”都是一个分配数组，形式与最优解相同，数组中的每个元素即为一个“基因”；
同时随机生成多个“个体”，依概率选择最优的两个个体作为“父母”，它们的“基因”组合出新的策略即为“子代”；
这样的操作，可以提取出“父母”中的优秀“基因”，通过多次重复，即可得到近优解。
需要注意，“伙伴”是游戏中的概念，和算法描述中的“个体”无关，其作用更接近“基因位置”。
'''

# 以下三个是需要根据自身需求修改的策略，包含想要的资源、能探索的最高关卡、以及自身伙伴的攻防属性
# 参数1，策略选择：0/1/2分别对应探索金币/木头/铁矿最多
explore_strategy = 0

# 参数2：目前能够探索的最高关卡（不能超过22）
explore_now = 22

# 参数3：自身伙伴战力，格式为[攻击,防御]，注意里面那个逗号是英文的
f_power = [[8703, 6746], [6536, 2514], [5160, 3680], [2253, 3258], [3126, 2226],
           [2150, 3168], [2913, 2260], [3580, 1586], [2373, 2698], [2763, 1860],
           [1433, 1454], [1560, 1268], [1413, 1386], [1583, 1208], [1850, 924],
           [1353, 1394], [1323, 1408], [1613, 1106], [1283, 1422]]
num_partners = len(f_power)

# 遗传算法参数，想调整性能可以改
pop_size = 200     # 遗传算法种群规模（每次迭代保留200个解）
gens = 10000         # 迭代次数（进化500代）
mut_rate = 0.1     # 变异概率（10%）

# 一些游戏数据，如有版本变更可以修改
# 每关的满收益战力需求
explore_need = [350, 900, 1200, 2200, 2800,
                4000, 4800, 8000, 9000, 10000,
                11000, 20000, 22000, 23000, 25000,
                35000, 51000, 54000, 57000, 65000,
                65000, 65000]

# 每关满收益金币数
explore_gold = [579432, 884664, 928632, 1017096, 1105560,
                1150056, 1238520, 1326984, 1547880, 1769304,
                1990224, 2212152, 2434608, 2657064, 2879520,
                3101976, 3324432, 3546888, 3769344, 4800000,
                4800000, 5040000]

# 每关满收益木头数
explore_wood = [600, 1200, 1800, 2400, 3000,
                3600, 4200, 4800, 5400, 6000,
                6600, 7200, 7800, 8400, 9000,
                9600, 10200, 10800, 11400, 13200,
                13200, 13680]

# 每关满收益铁矿数
explore_iron = [120, 240, 360, 480, 600,
                720, 840, 960, 1080, 1200,
                1320, 1440, 1560, 1680, 1800,
                1920, 2040, 2160, 2280, 3000,
                3360, 3600]

# 数据处理
# 计算伙伴实际战力
f_real = []
for i0 in range(num_partners):
    x = f_power[i0][0] + f_power[i0][1]
    f_real.append(x)
# print(f_real)

# 不同策略对应不同收益目标
if explore_strategy == 0:
    strategy_real = explore_gold[:explore_now]
elif explore_strategy == 1:
    strategy_real = explore_wood[:explore_now]
else:
    strategy_real = explore_iron[:explore_now]


# 具体函数
# 计算对应种群收益的函数（适应度）
def evaluate(individual):
    # 输入的individual是伙伴探索队列（种群中的个体），表现形式为一个数组，数组元素为对应位置伙伴要探索的关卡
    # 初始化关卡分配队列，是每个关卡有哪些伙伴
    level_assign = [[] for _ in range(explore_now)]
    # 遍历个体的每个基因（伙伴的分配）
    for i, lv in enumerate(individual):
        if lv > 0:  # lv=0表示该伙伴不分配到任何关卡；lv>0表示分配到第lv个关卡（1-based）
            level_assign[lv - 1].append(f_real[i])  # 转换为0-based索引存入

    total_gold = 0  # 总金币
    for j in range(explore_now):
        # 约束检查：每个关卡最多分配4人，超出则直接判为无效解（收益0）
        if len(level_assign[j]) > 4:
            return 0
        # 计算该关卡的总战力
        total_power = sum(level_assign[j])
        # 计算收益系数：若总战力≥需求则系数为1（全额金币），否则为比例值（实际战力/需求战力）
        ratio = min(1, total_power / explore_need[j])
        # 累加该关卡的收益（最大收益×系数），收益不存在小数
        total_gold += int(strategy_real[j] * ratio)
    return total_gold  # 返回总金币（适应度值，越大越好）


# 初始化候选集合（种群）
def init_population():
    # 生成POP_SIZE个个体，每个个体是长度为NUM_PARTNERS的列表，代表一种分配方式
    # 列表中每个元素是0~NUM_LEVELS的整数：0表示不分配，1~22表示分配到对应关卡
    return [[random.randint(1, explore_now) for _ in range(num_partners)]
            for _ in range(pop_size)]


# 选择
def select(pop, fitness):
    # pop是所有分配方式的集合（200个个体构成的种群）
    # fitness是一个数组，装着种群中所有个体的收益
    total = sum(fitness)  # 总适应度
    probs = [f / total for f in fitness]  # 每个个体被选中的概率，与对应收益成正比
    # 某种分配方式的收益越高，说明里面的具体策略越优秀，算法就会更倾向于在它的基础上改进
    # 有些分配方式可能总收益偏低，但里面某一基因也可能刚好是最优的（被其它拖了后腿），因此不能完全放弃
    # 按概率选择2个个体作为父母
    return random.choices(pop, weights=probs, k=2)


# 交叉
# select函数选出了比较优秀的两个分配方式
def crossover(p1, p2):
    # 随机选择一个交叉点（避免首尾）
    point = random.randint(1, num_partners - 2)
    # 生成子代：前半部分来自父代p1，后半部分来自父代p2
    return p1[:point] + p2[point:]


# 变异
# 可能最优解根本不在一开始生成的那200个策略里，偶尔要寻找一点新东西
def mutate(ind):
    # 遍历个体的每个基因（伙伴分配）
    for i in range(num_partners):
        # 以MUT_RATE（10%）的概率随机改变该基因
        if random.random() < mut_rate:
            ind[i] = random.randint(0, explore_now)  # 重新随机分配（0~22）
    return ind


# 主函数
# 初始化种群（生成初始候选解）
population = init_population()
# 迭代进化GENS代
for gen in tqdm(range(gens), desc="迭代进度"):
    # 计算当前种群中每个个体的适应度（总资源收益）
    fitness = [evaluate(ind) for ind in population]
    # 生成下一代种群
    new_pop = []
    for _ in range(pop_size):
        # 选择两个父母
        p1, p2 = select(population, fitness)
        # 交叉产生子代
        child = crossover(p1, p2)
        # 子代变异
        child = mutate(child)
        # 加入新种群
        new_pop.append(child)
    # 用新种群替换旧种群，进入下一代
    population = new_pop

# 找到最优解（适应度最高的个体）
best = max(population, key=evaluate)
if explore_strategy == 0:
    print("最优金币收益为:", evaluate(best))
elif explore_strategy == 1:
    print("最优木头收益为:", evaluate(best))
else:
    print("最优铁矿收益为:", evaluate(best))
print("分配方案:", best)          # 最优分配方案（每个伙伴的分配）
