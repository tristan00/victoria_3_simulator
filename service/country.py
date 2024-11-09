from typing import Dict, Optional, Union, List, ClassVar

from pydantic import BaseModel, ConfigDict

from models.action import Action, SwapProductionMethod, UpgradeBuilding, DowngradeBuilding, NoAction
from models.state import State, ModularBuilding
from service.agent import Agent


class Country(BaseModel):
    id: str
    agent: Agent
    states: Dict[str, State]
    current_construction: Optional[Action] = None
    ACTION_TYPES: ClassVar[Dict[str, int]] = {
        "SwapProductionMethod": 1,
        "Upgrade": 2,
        "Downgrade": 3,
        "NoAction": 4,
    }

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def convert_option_to_numeric(self, action: Action) -> Dict[str, Union[int, float]]:
        """Convert a single action to its numeric representation with a fixed-size output."""

        # Base fields common to all actions
        action_data = {
            "action_type": self.ACTION_TYPES[action.action_type],
            "state_id": hash(action.state_id) % 1000,
            "building_name": hash(action.building_name) % 1000,
            # Defaults for additional fields that may not be present in every action
            "new_production_method": -1,  # Use -1 as a placeholder if not applicable
        }

        # Specific fields for each action type
        if isinstance(action, SwapProductionMethod):
            # Convert the production method to an index
            production_method_index = list(self.states[action.state_id].get_building_by_name(
                action.building_name).production_methods.keys()).index(action.new_production_method)
            action_data["new_production_method"] = production_method_index

        return action_data

    def get_available_options(self) -> Dict[str, List[Action]]:
        """List all available actions for each building in each state."""
        options = {}
        for state_id, state in self.states.items():
            state_options = []
            for building in state.buildings:
                if isinstance(building, ModularBuilding):
                    current_method = building.production_method
                    for method in building.production_methods.keys():
                        if method != current_method:
                            state_options.append(
                                SwapProductionMethod(
                                    state_id=state_id,
                                    building_name=building.name,
                                    new_production_method=method
                                )
                            )

                if not self.current_construction and building.building_level < building.building_max_level:
                    state_options.append(
                        UpgradeBuilding(
                            state_id=state_id,
                            building_name=building.name
                        )
                    )

                if building.building_level >= 1:
                    state_options.append(
                        DowngradeBuilding(
                            state_id=state_id,
                            building_name=building.name
                        )
                    )
                state_options.append(NoAction(state_id=state_id, building_name = building.name))

            options[state_id] = state_options
        return options

    def execute_action(self, action: Action):
        if isinstance(action, SwapProductionMethod):
            self._swap_production_method(action)
        elif isinstance(action, UpgradeBuilding):
            self._start_upgrade(action)
        elif isinstance(action, DowngradeBuilding):
            self._downgrade_building(action)

    def _swap_production_method(self, action: SwapProductionMethod):
        state = self.states[action.state_id]
        building = state.get_building_by_name(action.building_name)
        if isinstance(building, ModularBuilding):
            building.swap_production_method(action.new_production_method)

    def _start_upgrade(self, action: UpgradeBuilding):
        if not self.current_construction:
            self.current_construction = action

    def _downgrade_building(self, action: DowngradeBuilding):
        state = self.states[action.state_id]
        building = state.get_building_by_name(action.building_name)
        if building.building_level > 1:
            building.building_level -= 1


    def update_construction_progress(self, construction_contribution: float):
        if self.current_construction:
            # Add the contributed amount to construction progress
            self.construction_progress += construction_contribution

            # Extract the state and building for the current construction action
            state_id = self.current_construction.state_id
            building_name = self.current_construction.building_name
            state = self.states[state_id]
            building = next((b for b in state.buildings if b.name == building_name), None)

            # If the accumulated progress meets or exceeds the build cost, complete the upgrade
            if building and self.construction_progress >= building.build_cost:
                building.building_level += 1
                self.construction_progress = 0.0  # Reset progress for the next construction
                self.current_construction = None  # Clear the current construction action
                print(f"Upgraded {building.name} in {state_id} to level {building.building_level}")

    def record_daily_state(self) -> Dict[str, Union[str, float]]:

        daily_record = {
            "under_construction": 1 if self.current_construction else 0,
            "construction_progress": self.construction_progress if self.current_construction else 0.0,
            "construction_target": hash(
                self.current_construction.building_name) % 1000 if self.current_construction else -1,
        }

        for state_id, state in self.states.items():
            for building in state.buildings:
                prefix = f"{state_id}_{building.name}"

                production_method_index = list(building.production_methods.keys()).index(
                    building.production_method) if building.production_method in building.production_methods else 0

                daily_record.update({
                    f"{prefix}_building_level": building.building_level,
                    f"{prefix}_building_max_level": building.building_max_level,
                    f"{prefix}_cash_reserve": building.cash_reserve,
                    f"{prefix}_production_method_index": production_method_index,
                    f"{prefix}_production_wood": building.get_daily_production().get("wood", 0.0),
                    f"{prefix}_production_tools": building.get_daily_production().get("tools", 0.0),
                    f"{prefix}_production_iron": building.get_daily_production().get("iron", 0.0),
                    f"{prefix}_production_coal": building.get_daily_production().get("coal", 0.0),
                    f"{prefix}_production_wheat": building.get_daily_production().get("wheat", 0.0),
                    f"{prefix}_consumption_wood": building.calculate_consumption().get("wood", 0.0),
                    f"{prefix}_consumption_tools": building.calculate_consumption().get("tools", 0.0),
                    f"{prefix}_consumption_iron": building.calculate_consumption().get("iron", 0.0),
                    f"{prefix}_consumption_coal": building.calculate_consumption().get("coal", 0.0),
                    f"{prefix}_consumption_wheat": building.calculate_consumption().get("wheat", 0.0),
                    f"{prefix}_wage_cost": building.calculate_wages(),
                    f"{prefix}_input_cost": building.calculate_consumption_cost(state.resources),
                    f"{prefix}_output_value": building.calculate_production_value(state.resources),
                    f"{prefix}_shortage_penalty": building.shortage_penalty,
                })

        return daily_record
