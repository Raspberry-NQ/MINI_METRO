# replay_buffer.py — 经验回放缓冲区

import random
from collections import deque

import torch


class ReplayBuffer:
    """存储和采样训练经验 (s, a, r, s', done)"""

    def __init__(self, capacity=100000):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        """存入一条经验

        Args:
            state: torch.Tensor (state_dim,)
            action: int
            reward: float
            next_state: torch.Tensor (state_dim,)
            done: bool
        """
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size):
        """随机采样一批经验, 返回张量形式"""
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        return (
            torch.stack(states),
            torch.tensor(actions, dtype=torch.long),
            torch.tensor(rewards, dtype=torch.float32),
            torch.stack(next_states),
            torch.tensor(dones, dtype=torch.float32),
        )

    def __len__(self):
        return len(self.buffer)
