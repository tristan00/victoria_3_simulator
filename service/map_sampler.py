import os
import random
from typing import Dict
import re

from models.state import ConstructionSector, CoalMine, IronMine, LoggingCamp, WheatFarm, ToolWorkshop, Construction, \
    Wheat, Coal, Iron, Tools, Wood, State

dir_path = 'C:\Program Files (x86)\Steam\steamapps\common\Victoria 3\game\map_data\state_regions'


def parse_state_file(file_path: str) -> State:
    # List all text files in the directory and randomly select one
    state_files = [file for file in os.listdir(dir_path) if file.endswith('.txt')]
    chosen_file = random.choice(state_files)
    file_path = os.path.join(dir_path, chosen_file)

    # Read the contents of the chosen file and find all state definitions
    with open(file_path, 'r') as file:
        content = file.read()

    # Find all state blocks in the file
    state_blocks = re.findall(r'(STATE_\w+ = {[^}]+})', content, re.DOTALL)
    # Select a random state block from within the file
    chosen_state_block = random.choice(state_blocks)

    # Extract state information from the chosen block
    state_id = re.search(r'id\s*=\s*(\d+)', chosen_state_block).group(1)
    capped_resources = dict(re.findall(r'(\w+)\s*=\s*(\d+)', chosen_state_block))

    # Initialize the state
    state = State(
        id=state_id,
        buildings=[],
        resources={
            "wood": Wood(quantity=1000.0),
            "tools": Tools(quantity=1000.0),
            "iron": Iron(quantity=1000.0),
            "coal": Coal(quantity=1000.0),
            "wheat": Wheat(quantity=1000.0),
            'construction': Construction(quantity=0)
        }
    )

    resource_building_map = {
        'bg_wheat_farms': WheatFarm,
        'bg_logging': LoggingCamp,
        'bg_iron_mining': IronMine,
        'bg_coal_mining': CoalMine
    }

    # Add basic buildings
    state.add_building(ConstructionSector(
        building_level=random.randint(1, 3),
        production_method=random.choice(list(ConstructionSector.production_methods.keys())),
        building_max_level=10
    ))
    state.add_building(ToolWorkshop(
        building_level=random.randint(1, 3),
        production_method=random.choice(list(ToolWorkshop.production_methods.keys())),
        building_max_level=20
    ))

    # Add buildings based on capped resources
    for resource, BuildingClass in resource_building_map.items():
        max_level = int(capped_resources.get(resource, 99))  # Set max to 99 if not found
        building_level = random.randint(1, 5) if max_level > 0 else 0
        state.add_building(BuildingClass(
            building_level=building_level,
            production_method=random.choice(list(BuildingClass.production_methods.keys())),
            building_max_level=max_level
        ))

    return state


def sample_state_from_directory(dir_path: str) -> State:
    # List all files in the directory
    state_files = [os.path.join(dir_path, file) for file in os.listdir(dir_path) if file.endswith('.txt')]

    # Randomly select one file
    selected_file = random.choice(state_files)
    print(f"Selected state file: {selected_file}")

    # Parse the selected file to create the state
    return parse_state_file(selected_file)


def get_random_state():
    return sample_state_from_directory(dir_path)