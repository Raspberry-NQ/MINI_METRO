# dueling_dqn.py — Dueling DQN 网络结构

import torch
import torch.nn as nn


class DuelingDQN(nn.Module):
    """
    Dueling DQN: Q(s, a) = V(s) + A(s, a) - mean(A(s, a))

    输入: 编码后的状态向量 (state_dim 维)
    输出: 每个动作的 Q 值 (n_actions 维)
    """

    def __init__(self, state_dim=186, n_actions=15, hidden_dim=256):
        super().__init__()

        # 共享特征提取层
        self.feature_layer = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )

        # 价值流 V(s): 状态本身有多好 → 输出 1 个标量
        self.value_stream = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
        )

        # 优势流 A(s,a): 每个动作比平均水平好多少 → 输出 n_actions 个标量
        self.advantage_stream = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, n_actions),
        )

    def forward(self, x):
        features = self.feature_layer(x)
        value = self.value_stream(features)           # (batch, 1)
        advantage = self.advantage_stream(features)    # (batch, n_actions)

        # Q(s,a) = V(s) + A(s,a) - mean(A(s,a))
        q_values = value + advantage - advantage.mean(dim=-1, keepdim=True)
        return q_values
