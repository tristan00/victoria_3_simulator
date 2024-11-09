from typing import Dict, List

from pydantic import BaseModel


class PopType(BaseModel):
    name: str
    base_income: float  # Average income for this pop type
    consumption_needs: Dict[str, float]  # Daily consumption needs by product name and quantity

    def calculate_daily_consumption(self) -> Dict[str, float]:
        """Calculate daily consumption needs for this pop type."""
        return {product: need for product, need in self.consumption_needs.items()}


class Pop(BaseModel):
    pop_type: PopType
    population_count: int
    employed: int
    unemployed: int

    def calculate_total_income(self) -> float:
        """Calculate total daily income for this pop based on employment."""
        return self.pop_type.base_income * self.employed

    def calculate_daily_consumption(self) -> Dict[str, float]:
        """Calculate total daily consumption for this pop based on population size."""
        return {
            product: need * self.population_count
            for product, need in self.pop_type.calculate_daily_consumption().items()
        }


class StatePopulation(BaseModel):
    pops: List[Pop]  # All population groups in the state

    def calculate_state_consumption(self) -> Dict[str, float]:
        """Aggregate daily consumption needs for the entire state population."""
        total_consumption = {}
        for pop in self.pops:
            daily_consumption = pop.calculate_daily_consumption()
            for product, amount in daily_consumption.items():
                total_consumption[product] = total_consumption.get(product, 0) + amount
        return total_consumption

    def calculate_total_income(self) -> float:
        """Calculate total income for the entire population in the state."""
        return sum(pop.calculate_total_income() for pop in self.pops)
