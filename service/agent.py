import os
import uuid
from typing import Tuple

import torch
import torch.nn as nn
import numpy as np


agent_directory_path = r'C:\Users\trist\Documents\victoria_3_sim\agents'


class Agent:

    def __init__(self, agent_id, input_size, hidden_sizes, weights):
        self.agent_id = agent_id
        all_sizes = [input_size] + hidden_sizes + [1]

        self.model_layers = nn.ModuleList()
        for i in range(len(all_sizes) - 1):
            layer = nn.Linear(all_sizes[i], all_sizes[i + 1])

            weight, bias = weights[i]
            layer.weight = nn.Parameter(weight)
            layer.bias = nn.Parameter(bias)

            self.model_layers.append(layer)

        self.activation = nn.ReLU()
        self.save_weights(agent_directory_path)


    def evaluate_action(self, daily_state, option_numeric):
        input_vector = np.concatenate([list(daily_state.values()), list(option_numeric.values())])
        input_tensor = torch.tensor(input_vector, dtype=torch.float32)

        if input_tensor.shape[0] != self.model_layers[0].in_features:
            raise ValueError(f"Input size mismatch: expected {self.model_layers[0].in_features}, "
                             f"but got {input_tensor.shape[0]}")

        x = input_tensor
        for i, layer in enumerate(self.model_layers):
            x = layer(x)
            if i < len(self.model_layers) - 1:
                x = self.activation(x)
        return x.item()

    def save_weights(self, directory_path):
        os.makedirs(directory_path, exist_ok=True)
        file_path = os.path.join(directory_path, f"{self.agent_id}.pt")
        torch.save({f"layer_{i}": (layer.weight, layer.bias) for i, layer in enumerate(self.model_layers)}, file_path)
        print(f"Weights saved for agent {self.agent_id} at {file_path}")


def generate_random_weights(layer_sizes):
    weights = []
    for i in range(len(layer_sizes) - 1):
        weight_shape = (layer_sizes[i + 1], layer_sizes[i])
        bias_shape = (layer_sizes[i + 1],)
        weight = torch.randn(weight_shape) * np.sqrt(2. / layer_sizes[i])
        bias = torch.randn(bias_shape)
        weights.append((weight, bias))
    return weights


def pick_options(agent: Agent, options_numeric: list, daily_state: dict):
    scored_options = []
    for option in options_numeric:
        score = agent.evaluate_action(daily_state, option)
        scored_options.append((option, score))

    scored_options.sort(key=lambda x: x[1], reverse=True)
    top_option = scored_options[0][0]

    return top_option


def make_random_agent(input_size: int, output_size: int, hidden_layer_sizes: Tuple[int, ...]):
    # Combine input size, hidden layer sizes, and output size into a single list for layer sizes
    layer_sizes = [input_size] + list(hidden_layer_sizes) + [output_size]
    hidden_sizes = list(hidden_layer_sizes)
    return Agent(agent_id=str(uuid.uuid4()), input_size=input_size, hidden_sizes=hidden_sizes, weights=generate_random_weights(layer_sizes))