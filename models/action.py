from typing import Dict, Union

from pydantic import BaseModel


class Action(BaseModel):
    action_type: str
    state_id: str
    building_name: str

    def to_numeric(self, action_types) -> Dict[str, Union[int, float]]:
        # Basic numeric structure with state and building converted using hash
        return {
            "action_type": action_types[self.action_type],
            "state_id": hash(self.state_id) % 1000,
            "building_name": hash(self.building_name) % 1000,
        }


class SwapProductionMethod(Action):
    action_type: str = "SwapProductionMethod"
    new_production_method: str

    def to_numeric(self, action_types) -> Dict[str, Union[int, float]]:
        # Add specific conversion for production method
        numeric_rep = super().to_numeric(action_types)
        production_method_index = hash(self.new_production_method) % 100
        numeric_rep["new_production_method"] = production_method_index
        return numeric_rep


class UpgradeBuilding(Action):
    action_type: str = "Upgrade"

    def to_numeric(self, action_types) -> Dict[str, Union[int, float]]:
        return super().to_numeric(action_types)


class DowngradeBuilding(Action):
    action_type: str = "Downgrade"
    def to_numeric(self, action_types) -> Dict[str, Union[int, float]]:
        return super().to_numeric(action_types)


class NoAction(Action):
    action_type: str = "NoAction"

    def to_numeric(self, action_types) -> Dict[str, Union[int, float]]:
        return super().to_numeric(action_types)
