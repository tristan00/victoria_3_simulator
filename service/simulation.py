import csv
import os
import random
import uuid
import pandas as pd
import numpy as np
import torch

from models.state import (
    State, Wood, Tools, Iron, Coal, Wheat, LoggingCamp, ToolWorkshop, IronMine, WheatFarm, CoalMine,
    Construction, ConstructionSector,
)
from service.country import Country
from datetime import date, timedelta
from service.agent import make_random_agent, Agent, pick_options
from service.map_sampler import get_random_state

output_file_path =r'C:\Users\trist\Documents\victoria_3_sim\agent_logs.csv'
final_scores_file = r'C:\Users\trist\Documents\victoria_3_sim\final_scores.csv'
agent_directory_path = r'C:\Users\trist\Documents\victoria_3_sim\agents'


def calculate_total_cash_reserves(state: State) -> float:
    return sum(building.cash_reserve for building in state.buildings)


def write_final_score(agent_id, generation_id, generation_num, final_score):
    """Write the final score to a summary file."""
    summary_file_path = "final_scores.csv"
    if not os.path.exists(summary_file_path):
        # Create the file and write header if it does not exist
        with open(summary_file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            header = ['agent_id', 'generation_id', 'generation_num', 'final_score']
            writer.writerow(header)

    # Append final score to the summary file
    with open(summary_file_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([agent_id, generation_id, generation_num, final_score])



def write_daily_log(agent_id, daily_state, chosen_action):

    """Write daily log data to a CSV file."""
    if not os.path.exists(output_file_path):

        with open(output_file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            header = ['agent_id'] + list(daily_state.keys()) + ['chosen_action']
            writer.writerow(header)


    # Write a row of data for the day
    with open(output_file_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        row = [agent_id] + list(daily_state.values()) + [chosen_action]
        writer.writerow(row)


def run_simulation(country: Country, agent: Agent, start_date: date, generation_id: str, days_to_run: int = 1000, generation_num:int = 0):

    current_date = start_date
    for day in range(days_to_run):
        print(f"\nDay {day + 1} - {current_date}")

        options = country.get_available_options()['State1']
        daily_state = country.record_daily_state()
        options_numeric = [country.convert_option_to_numeric(option) for option in options]
        top_option = pick_options(agent, options_numeric, daily_state)
        country.execute_action(top_option)

        chosen_action_str = {
            "action_type": top_option["action_type"],
            "state_id": top_option["state_id"],
            "building_name": top_option["building_name"],
            "additional_info": top_option.get("new_production_method")
        }

        write_daily_log(agent.agent_id, daily_state, chosen_action_str)

        for state_id, state in country.states.items():
            print(f"\nState {state_id}")

            building_productions = state.calculate_building_productions()

            print("Local Prices of Products:")
            for product_name, product in state.resources.items():
                print(f"  {product_name.capitalize()}: {product.local_price:.2f}")

            for building_name, production in building_productions.items():
                building = next(b for b in state.buildings if b.name == building_name)
                throughput_multiplier = building.calculate_throughput_multiplier()
                print(f"\nBuilding: {building_name}")
                print(f"  Throughput Multiplier: {throughput_multiplier:.2f}")
                print(f"  Cash Balance: {building.cash_reserve:.2f}")

        current_date += timedelta(days=1)

    final_score = calculate_total_cash_reserves(country.states['State1'])
    write_final_score(agent.agent_id, generation_id, generation_num, final_score)

    print("\nSimulation complete.")



def run_simulations(agent, state, generation_id):
    country = Country(id="Country1", states={"State1": state}, agent=agent)
    run_simulation(country, agent=agent, start_date=date.today(), days_to_run=5000, generation_id = generation_id)



def load_previous_generation(generation_id, num_survivors):
    """Load top-performing agents from previous generation based on final scores."""
    if not os.path.exists(final_scores_file):
        return []  # No previous generation exists

    scores_df = pd.read_csv(final_scores_file)
    previous_gen_agents = scores_df[scores_df['generation_id'] == generation_id]
    top_agents = previous_gen_agents.nlargest(num_survivors, 'final_score')

    return [agent_id for agent_id in top_agents['agent_id']]


def load_agent_weights(agent_id):
    """Load agent weights from a saved file."""
    file_path = os.path.join(agent_directory_path, f"{agent_id}.pt")
    if os.path.exists(file_path):
        weights = torch.load(file_path)
        return [(layer_weight, layer_bias) for layer_weight, layer_bias in weights.values()]
    else:
        raise FileNotFoundError(f"Weight file for agent {agent_id} not found.")


def generate_new_generation(previous_generation_id, num_of_candidates=100, survivor_rate=0.1, mutate_rate=0.4,
                            random_rate=0.5):
    """Generate a new generation of agents."""
    assert abs(survivor_rate + mutate_rate + random_rate - 1.0) < 1e-5, "Rates must sum to 1."

    num_survivors = int(survivor_rate * num_of_candidates)
    num_mutated = int(mutate_rate * num_of_candidates)
    num_random = num_of_candidates - num_survivors - num_mutated

    # Load top survivors from previous generation
    survivors = []
    if previous_generation_id:
        top_agent_ids = load_previous_generation(previous_generation_id, num_survivors)
        for agent_id in top_agent_ids:
            weights = load_agent_weights(agent_id)
            survivors.append(Agent(agent_id=agent_id, input_size=115, hidden_sizes=[128, 64, 32], weights=weights))

    # Generate Mutated Agents
    mutated_agents = []
    for _ in range(num_mutated):
        if survivors:
            parent = random.choice(survivors)
            mutated_weights = [
                (weight + torch.randn(weight.shape) * 0.1, bias + torch.randn(bias.shape) * 0.1)
                for weight, bias in parent.model_layers
            ]
            mutated_agents.append(
                Agent(agent_id=str(uuid.uuid4()), input_size=115, hidden_sizes=[128, 64, 32], weights=mutated_weights)
            )

    # Generate Random Agents
    random_agents = [
        make_random_agent(input_size=115, output_size=1, hidden_layer_sizes=(128, 64, 32))
        for _ in range(num_random)
    ]

    return survivors + mutated_agents + random_agents


def run_generations(num_of_candidates=100, pass_rate=0.1, previous_generation_id=None, generation_num=0,
                    generations=10, experiment_id=None, days_to_run=1000):
    """Run a specified number of generations, saving each generation's results."""
    for gen in range(generations):
        generation_id = f"gen_{experiment_id}_{gen + generation_num}"

        # Generate new agents for the generation
        agents = generate_new_generation(
            previous_generation_id=previous_generation_id,
            num_of_candidates=num_of_candidates,
            survivor_rate=pass_rate,
            mutate_rate=(1 - pass_rate) * 0.5,
            random_rate=(1 - pass_rate) * 0.5
        )

        # Simulate each agent's performance
        for agent in agents:
            state = get_random_state()
            country = Country(id="Country1", states={"State1": state}, agent=agent)
            run_simulation(country, agent=agent, start_date=date.today(), generation_id=generation_id, generation_num=generation_num, days_to_run=6000)

        # Update for next generation
        previous_generation_id = generation_id
        print(f"Generation {generation_id} complete.")


if __name__ == '__main__':
    run_generations(num_of_candidates=10,
                    pass_rate=0.4,
                    previous_generation_id=None,
                    generation_num=0,
                    generations=10,
                    experiment_id=str(uuid.uuid4()),
                    days_to_run=1000
                    )

