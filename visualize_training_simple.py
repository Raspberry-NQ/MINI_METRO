# visualize_training_simple.py — 训练过程可视化工具（纯文本版）
#
# 用于显示训练过程中的关键指标，无需matplotlib

import os
import sys


def plot_training_history_text(log_file='training_log.txt'):
    """从日志文件绘制训练历史（纯文本版）"""
    if not os.path.exists(log_file):
        print(f"日志文件不存在: {log_file}")
        return

    # 读取日志数据
    episodes = []
    rewards = []
    survivals = []
    arrived = []
    epsilons = []
    steps = []

    with open(log_file, 'r') as f:
        lines = f.readlines()
        for line in lines[1:]:  # 跳过标题行
            parts = line.strip().split(',')
            if len(parts) >= 6:
                episodes.append(int(parts[0]))
                rewards.append(float(parts[1]))
                survivals.append(float(parts[2]))
                arrived.append(float(parts[3]))
                epsilons.append(float(parts[4]))
                steps.append(int(parts[5]))

    if not episodes:
        print("日志文件中没有训练数据")
        return

    # 打印训练摘要
    print("\n" + "="*60)
    print("训练历史摘要")
    print("="*60)

    print(f"\n总Episode数: {len(episodes)}")
    print(f"初始奖励: {rewards[0]:.2f}")
    print(f"最终奖励: {rewards[-1]:.2f}")
    print(f"奖励提升: {rewards[-1] - rewards[0]:.2f} ({(rewards[-1]/rewards[0]-1)*100:.1f}%)")

    print(f"\n初始到达乘客: {arrived[0]:.1f}")
    print(f"最终到达乘客: {arrived[-1]:.1f}")
    print(f"乘客提升: {arrived[-1] - arrived[0]:.1f} ({(arrived[-1]/arrived[0]-1)*100:.1f}%)")

    print(f"\n初始Epsilon: {epsilons[0]:.4f}")
    print(f"最终Epsilon: {epsilons[-1]:.4f}")
    print(f"Epsilon衰减: {epsilons[0] - epsilons[-1]:.4f}")

    print(f"\n总训练步数: {steps[-1]}")

    # 打印趋势
    print("\n" + "="*60)
    print("训练趋势")
    print("="*60)

    # 每5个episode打印一次
    print("\nEpisode | Reward | Arrived | Epsilon | Steps")
    print("-" * 50)
    for i in range(0, len(episodes), max(1, len(episodes)//10)):
        ep = episodes[i]
        rwd = rewards[i]
        arr = arrived[i]
        eps = epsilons[i]
        stp = steps[i]
        print(f"{ep:7d} | {rwd:6.2f} | {arr:7.1f} | {eps:7.4f} | {stp:6d}")

    # 最后一个episode
    if episodes[-1] != episodes[i]:
        print(f"{episodes[-1]:7d} | {rewards[-1]:6.2f} | {arrived[-1]:7.1f} | {epsilons[-1]:7.4f} | {steps[-1]:6d}")

    print("\n" + "="*60)

    # 保存为简单的文本图表
    chart_file = 'training_chart.txt'
    with open(chart_file, 'w') as f:
        f.write("="*60 + "\n")
        f.write("训练过程图表\n")
        f.write("="*60 + "\n\n")

        f.write("奖励曲线:\n")
        max_reward = max(rewards)
        for i, (ep, rwd) in enumerate(zip(episodes, rewards)):
            bar_len = int(rwd / max_reward * 40)
            bar = '#' * bar_len
            f.write(f"{ep:5d} |{bar} {rwd:.2f}\n")

        f.write("\n到达乘客:\n")
        max_arrived = max(arrived)
        for i, (ep, arr) in enumerate(zip(episodes, arrived)):
            bar_len = int(arr / max_arrived * 40)
            bar = '#' * bar_len
            f.write(f"{ep:5d} |{bar} {arr:.1f}\n")

        f.write("\nEpsilon衰减:\n")
        for i, (ep, eps) in enumerate(zip(episodes, epsilons)):
            bar_len = int(eps * 40)
            bar = '#' * bar_len
            f.write(f"{ep:5d} |{bar} {eps:.4f}\n")

    print(f"训练图表已保存到: {chart_file}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="训练可视化工具（纯文本版）")
    parser.add_argument("--log", type=str, default='training_log.txt', help="训练日志文件路径")
    args = parser.parse_args()

    plot_training_history_text(args.log)