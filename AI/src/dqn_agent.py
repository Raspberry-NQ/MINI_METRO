# dqn_agent.py — Dueling DQN 智能体

import random

import torch
import torch.nn as nn

from .dueling_dqn import DuelingDQN
from .replay_buffer import ReplayBuffer


class DQNAgent:
    """Dueling DQN 智能体

    包含:
      - 在线网络 (每步更新)
      - 目标网络 (定期从在线网络复制, 稳定训练)
      - 经验回放缓冲区
      - ε-greedy 探索策略
    """

    def __init__(self, state_dim=186, n_actions=15, hidden_dim=256):
        self.n_actions = n_actions
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # 在线网络
        self.online_net = DuelingDQN(state_dim, n_actions, hidden_dim).to(self.device)
        # 目标网络
        self.target_net = DuelingDQN(state_dim, n_actions, hidden_dim).to(self.device)
        self.target_net.load_state_dict(self.online_net.state_dict())
        self.target_net.eval()

        self.optimizer = torch.optim.Adam(self.online_net.parameters(), lr=1e-4)
        self.buffer = ReplayBuffer(capacity=100000)

        # 超参数
        self.gamma = 0.99
        self.epsilon = 1.0
        self.eps_min = 0.05
        self.eps_decay = 0.9995
        self.batch_size = 64
        self.target_update_freq = 500
        self.step_count = 0

    def select_action(self, state_tensor, valid_mask):
        """选择动作 (ε-greedy)

        Args:
            state_tensor: 编码后的状态 (1, state_dim) 或 (state_dim,)
            valid_mask: list[bool], 哪些动作合法

        Returns:
            int: 选择的动作编号
        """
        if random.random() < self.epsilon:
            # 随机探索: 只从合法动作中选
            valid_actions = [i for i, v in enumerate(valid_mask) if v]
            return random.choice(valid_actions)

        # 利用: 选 Q 值最高的合法动作
        with torch.no_grad():
            if state_tensor.dim() == 1:
                state_tensor = state_tensor.unsqueeze(0)
            q_values = self.online_net(state_tensor.to(self.device))
            mask_tensor = torch.tensor(valid_mask, dtype=torch.bool).to(self.device)
            q_values[0][~mask_tensor] = -1e9
            return q_values.argmax(dim=1).item()

    def update(self):
        """从 buffer 采样并更新网络

        Returns:
            float or None: loss 值, 如果经验不够则返回 None
        """
        if len(self.buffer) < self.batch_size:
            return None

        states, actions, rewards, next_states, dones = self.buffer.sample(self.batch_size)
        states = states.to(self.device)
        actions = actions.to(self.device)
        rewards = rewards.to(self.device)
        next_states = next_states.to(self.device)
        dones = dones.to(self.device)

        # 当前 Q 值: Q(s, a)
        current_q = self.online_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)

        # 目标 Q 值: r + γ * max_a' Q_target(s', a')
        with torch.no_grad():
            next_q = self.target_net(next_states).max(dim=1)[0]
            target_q = rewards + self.gamma * next_q * (1 - dones)

        # Huber Loss
        loss = nn.SmoothL1Loss()(current_q, target_q)

        # 反向传播
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.online_net.parameters(), 10)
        self.optimizer.step()

        # 定期更新目标网络
        self.step_count += 1
        if self.step_count % self.target_update_freq == 0:
            self.target_net.load_state_dict(self.online_net.state_dict())

        # ε 衰减
        self.epsilon = max(self.eps_min, self.epsilon * self.eps_decay)

        return loss.item()

    def save(self, path):
        """保存模型"""
        torch.save({
            'online_net': self.online_net.state_dict(),
            'target_net': self.target_net.state_dict(),
            'optimizer': self.optimizer.state_dict(),
            'epsilon': self.epsilon,
            'step_count': self.step_count,
        }, path)

    def load(self, path):
        """加载模型"""
        checkpoint = torch.load(path, map_location=self.device)
        self.online_net.load_state_dict(checkpoint['online_net'])
        self.target_net.load_state_dict(checkpoint['target_net'])
        self.optimizer.load_state_dict(checkpoint['optimizer'])
        self.epsilon = checkpoint.get('epsilon', self.eps_min)
        self.step_count = checkpoint.get('step_count', 0)
        print(f"模型已加载: {path}, epsilon={self.epsilon:.4f}, steps={self.step_count}")
