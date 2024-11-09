from typing import Dict, Optional, List, ClassVar
from pydantic import BaseModel


class Product(BaseModel):
    name: str
    base_price: float
    quantity: float
    local_price: float = 0.0
    max_price_cap: float = 1.75

    def adjust_price(self, buy_orders: float, sell_orders: float, adjustment_rate: float = 0.05):
        """
        Adjust price based on buy and sell orders.
        Price moves incrementally towards equilibrium, capped by max_price_cap.
        """
        if sell_orders > 0:
            demand_supply_ratio = buy_orders / sell_orders
            target_price = self.base_price * demand_supply_ratio
            self.local_price += adjustment_rate * (target_price - self.local_price)
        else:
            self.local_price += adjustment_rate * (self.base_price * self.max_price_cap - self.local_price)

        self.local_price = max(self.base_price, min(self.local_price, self.base_price * self.max_price_cap))


class Wood(Product):
    def __init__(self, quantity: float):
        super().__init__(name="wood", base_price=10.0, quantity=quantity)

class Tools(Product):
    def __init__(self, quantity: float):
        super().__init__(name="tools", base_price=20.0, quantity=quantity)

class Iron(Product):
    def __init__(self, quantity: float):
        super().__init__(name="iron", base_price=15.0, quantity=quantity)

class Coal(Product):
    def __init__(self, quantity: float):
        super().__init__(name="coal", base_price=8.0, quantity=quantity)

class Wheat(Product):
    def __init__(self, quantity: float):
        super().__init__(name="wheat", base_price=5.0, quantity=quantity)


class Construction(Product):
    def __init__(self, quantity: float):
        super().__init__(name="construction", base_price=0.0, quantity=quantity, local_price=0.0)


class Employee(BaseModel):
    name: str
    wage: float
    count: int


class Building(BaseModel):
    name: str
    build_cost: float
    cash_reserve: float
    building_level: int
    building_max_level: int
    production: Dict[str, float]
    consumption: Dict[str, float]
    employee: Dict[str, Employee]
    base_throughput_bonus: Optional[float] = 0.0
    shortage_penalty: Optional[float] = 0.0

    def calculate_buy_orders(self) -> Dict[str, float]:
        return {resource: quantity * self.building_level for resource, quantity in self.consumption.items()}

    def calculate_sell_orders(self) -> Dict[str, float]:
        throughput_multiplier = self.calculate_throughput_multiplier()

        adjusted_sell_orders = {
            product: quantity * self.building_level * throughput_multiplier
            for product, quantity in self.production.items()
        }
        return adjusted_sell_orders


    def get_throughput_bonus(self) -> float:
        if self.building_level > 1:
            throughput_bonus = 1 + ((self.building_level - 1) * 0.01)
        else:
            throughput_bonus = 1.0
        return throughput_bonus

    def calculate_throughput_multiplier(self) -> float:
        total_bonus = self.get_throughput_bonus() / 100
        effective_multiplier = 1 + total_bonus - self.shortage_penalty
        return max(effective_multiplier, 0)

    def get_daily_production(self) -> Dict[str, float]:
        """Calculate production adjusted for input shortages."""
        throughput_multiplier = self.calculate_throughput_multiplier()
        adjusted_production = {
            product: quantity * self.building_level * throughput_multiplier * (1/ 7)
            for product, quantity in self.production.items()
        }
        return adjusted_production

    def calculate_consumption(self) -> Dict[str, float]:
        """Calculate adjusted consumption based on building level and throughput."""
        throughput_multiplier = self.calculate_throughput_multiplier()
        return {product: quantity * self.building_level * throughput_multiplier * (1/ 7)
                for product, quantity in self.consumption.items()}

    def calculate_wages(self) -> float:
        """Calculate the total wages for all employees in the building."""
        return sum((1/365) * employee.wage * employee.count * self.building_level for employee in self.employee.values())

    def calculate_consumption_cost(self, product_prices: Dict[str, Product]) -> float:
        """Calculate the total cost of consumed resources based on local prices."""
        return sum(
            (self.consumption[resource] * self.building_level) * product_prices[resource].local_price
            for resource in self.consumption
        )

    def calculate_production_value(self, product_prices: Dict[str, Product]) -> float:
        """Calculate the total value of produced goods based on local prices."""
        daily_production = self.get_daily_production()
        return sum(
            daily_production[product] * product_prices[product].local_price
            for product in daily_production
        )

    def print_daily_costs(self, product_prices: Dict[str, Product]):
        """Print daily input cost, output value, wage cost, and total cost for the building."""
        input_cost = self.calculate_consumption_cost(product_prices)
        output_value = self.calculate_production_value(product_prices)
        wage_cost = self.calculate_wages()

        total_daily_cost = input_cost + wage_cost - output_value

        print(f"{self.name} - Input Cost: {input_cost:.2f}")
        print(f"{self.name} - Output Value: {output_value:.2f}")
        print(f"{self.name} - Wage Cost: {wage_cost:.2f}")
        print(f"{self.name} - Total Daily Cost: {total_daily_cost:.2f}\n")

    def update_cash_balance(self, product_prices: Dict[str, Product]):
        """Update cash balance based on sales revenue and wage expenses."""
        # Revenue from selling produced goods
        production = self.get_daily_production()
        revenue = sum(production[product] * product_prices[product].local_price for product in production)

        # Expenses from wages
        expenses = self.calculate_wages()

        # Update cash reserve
        self.cash_reserve += revenue - expenses
    def update_shortage_penalty(self, allocated_resources: Dict[str, float]):
        """
        Update shortage penalty based on resource availability.
        Increment by 1% if in shortage, up to a maximum of 50% or the shortage ratio cap.
        """
        max_penalty_based_on_shortage = 0.0

        for input_good, required_quantity in self.consumption.items():
            total_required = required_quantity * self.building_level
            available_quantity = allocated_resources.get(input_good, 0.0)

            if available_quantity < total_required:
                # Calculate shortage ratio as the percentage of required goods missing
                shortage_ratio = 1 - (available_quantity / total_required)
                max_penalty_based_on_shortage = max(max_penalty_based_on_shortage, shortage_ratio)

        if max_penalty_based_on_shortage > 0:
            self.shortage_penalty = min(self.shortage_penalty + 0.01, 0.5, max_penalty_based_on_shortage)
        else:
            self.shortage_penalty = 0.0


class ModularBuilding(Building):
    def __init__(self, name: str, build_cost: float, cash_reserve: float, building_level: int, building_max_level: int, production_config: dict, employee_config: dict):

        super().__init__(
            name=name,
            build_cost=build_cost,
            cash_reserve=cash_reserve,
            building_level=building_level,
            building_max_level=building_max_level,
            production=production_config["production"],
            consumption=production_config["consumption"],
            employee=employee_config,
        )
        self.production_method = None

    def swap_production_method(self, method_name: str):
        """Switch the building to a different production method."""
        if method_name in self.production_methods:
            new_config = self.production_methods[method_name]
            self.production = new_config["production"]
            self.consumption = new_config["consumption"]
            self.production_method = method_name
            print(f"{self.name} production method changed to {method_name}.")
        else:
            print(f"Production method {method_name} is not available for {self.name}.")


class LoggingCamp(ModularBuilding):
    production_methods: ClassVar[Dict[str, Dict[str, Dict[str, float]]]] = {
        "SimpleForestry": {
            "production": {"wood": 30.0},
            "consumption": {"tools": 5.0},
        },
        "SawMills": {
            "production": {"wood": 50.0},
            "consumption": {"tools": 10.0},
        },
    }
    employee_config: ClassVar[Dict[str, Dict[str, Dict[str, float]]]] = {
        "SimpleForestry": {
            "shopkeeper": Employee(name="shopkeeper", wage=1.0, count=500),
            "laborer": Employee(name="laborer", wage=1.0, count=4500),
        },
        "SawMills": {
            "shopkeeper": Employee(name="shopkeeper", wage=1.0, count=500),
            "laborer": Employee(name="laborer", wage=1.0, count=4000),
            "machinist": Employee(name="machinist", wage=1.0, count=500),
        }
    }
    production_method: str = None


    def __init__(self, building_level: int = 0,  building_max_level: int = 0, production_method: str = "SimpleForestry"):
        super().__init__(
            name="Logging Camp",
            build_cost=200,
            cash_reserve=0,
            building_level=building_level,
            building_max_level=building_max_level,
            production_config=self.production_methods[production_method],
            employee_config=self.employee_config[production_method]
        )
        self.production_method = production_method


class CoalMine(ModularBuilding):
    production_methods: ClassVar[Dict[str, Dict[str, Dict[str, float]]]] = {
        "PicksShovels": {
            "production": {"coal": 25.0},
            "consumption": {"tools": 5.0},
        },
        "AtmosphericEnginePump": {
            "production": {"coal": 40.0},
            "consumption": {"tools": 10.0},
        },
    }
    employee_config: ClassVar[Dict[str, Dict[str, Dict[str, float]]]] = {
        "PicksShovels": {
            "shopkeeper": Employee(name="shopkeeper", wage=1.0, count=500),
            "miner": Employee(name="miner", wage=1.0, count=3000),
        },
        "AtmosphericEnginePump": {
            "shopkeeper": Employee(name="shopkeeper", wage=1.0, count=500),
            "miner": Employee(name="miner", wage=1.0, count=3000),
        },
    }
    production_method: str = None

    def __init__(self, building_level: int = 0,  building_max_level: int = 0, production_method: str = "PicksShovels"):
        super().__init__(
            name="Coal Mine",
            build_cost=400,
            cash_reserve=0,
            building_level=building_level,
            building_max_level=building_max_level,
            production_config=self.production_methods[production_method],
            employee_config=self.employee_config[production_method]
        )
        self.production_method = production_method


class ToolWorkshop(ModularBuilding):
    production_methods: ClassVar[Dict[str, Dict[str, Dict[str, float]]]] = {
        "CrudeTools": {
            "production": {"tools": 15.0},
            "consumption": {"wood": 5.0},
        },
        "WroughtIronTools": {
            "production": {"tools": 30.0},
            "consumption": {"iron": 10.0, "wood": 5.0},
        },
    }
    employee_config: ClassVar[Dict[str, Dict[str, Dict[str, float]]]] = {
        "CrudeTools": {
            "shopkeeper": Employee(name="shopkeeper", wage=1.0, count=500),
            "artisan": Employee(name="artisan", wage=1.0, count=1500),
        },
        "WroughtIronTools": {
            "shopkeeper": Employee(name="shopkeeper", wage=1.0, count=500),
            "machinist": Employee(name="machinist", wage=1.0, count=2500),
        },
    }
    production_method: str = None

    def __init__(self, building_level: int = 0,  building_max_level: int = 0, production_method: str = "CrudeTools"):
        super().__init__(
            name="Tool Workshop",
            build_cost=500,
            cash_reserve=0,
            building_level=building_level,
            building_max_level=building_max_level,
            production_config=self.production_methods[production_method],
            employee_config=self.employee_config[production_method]
        )

        self.production_method = production_method


class WheatFarm(ModularBuilding):
    production_methods: ClassVar[Dict[str, Dict[str, Dict[str, float]]]] = {
        "OxPoweredPlows": {
            "production": {"wheat": 25.0},
            "consumption": {},
        },
        "HarvestingTools": {
            "production": {"wheat": 35.0},
            "consumption": {"tools": 2.0},
        },
    }
    employee_config: ClassVar[Dict[str, Dict[str, Dict[str, float]]]] = {
        "OxPoweredPlows": {
            "farmer": Employee(name="farmer", wage=1.0, count=1000),
            "laborer": Employee(name="laborer", wage=1.0, count=4000),
        },
        "HarvestingTools": {
            "farmer": Employee(name="farmer", wage=1.0, count=1000),
            "laborer": Employee(name="laborer", wage=1.0, count=3000),
        },
    }
    production_method: str = None

    def __init__(self, building_level: int = 0,  building_max_level: int = 0, production_method: str = "OxPoweredPlows"):
        super().__init__(
            name="Wheat Farm",
            build_cost=200,
            cash_reserve=0,
            building_level=building_level,
            building_max_level=building_max_level,
            production_config=self.production_methods[production_method],
            employee_config=self.employee_config[production_method]
        )
        self.production_method = production_method


class IronMine(ModularBuilding):
    production_methods: ClassVar[Dict[str, Dict[str, Dict[str, float]]]] = {
        "PicksShovels": {
            "production": {"iron": 20.0},
            "consumption": {"tools": 5.0},
        },
        "AtmosphericEnginePump": {
            "production": {"iron": 40.0},
            "consumption": {"tools": 10.0, "coal": 5.0},
        },
    }
    employee_config: ClassVar[Dict[str, Dict[str, Dict[str, float]]]] = {
        "PicksShovels": {
            "shopkeeper": Employee(name="shopkeeper", wage=1.0, count=500),
            "miner": Employee(name="miner", wage=1.0, count=3000),
        },
        "AtmosphericEnginePump": {
            "shopkeeper": Employee(name="shopkeeper", wage=1.0, count=500),
            "miner": Employee(name="miner", wage=1.0, count=3000),
        },
    }
    production_method: str = None

    def __init__(self, building_level: int = 0,  building_max_level: int = 0, production_method: str = "PicksShovels"):

        super().__init__(
            name="Iron Mine",
            build_cost=400,
            cash_reserve=0,
            building_level=building_level,
            building_max_level=building_max_level,
            production_config=self.production_methods[production_method],
            employee_config=self.employee_config[production_method]
        )
        self.production_method = production_method


class ConstructionSector(ModularBuilding):
    production_methods: ClassVar[Dict[str, Dict[str, Dict[str, float]]]] = {
        "NoConstruction": {
            "production": {"construction": 0.0},
            "consumption": {"wood": 0.0},
        },
        "WoodenBuilding": {
            "production": {"construction": 20.0},
            "consumption": {"wood": 10.0},
        },
        "IronBuilding": {
            "production": {"construction": 30.0},
            "consumption": {"iron": 15.0},
        },
    }
    employee_config: ClassVar[Dict[str, Dict[str, Dict[str, float]]]] = {
        "NoConstruction": {
            "carpenter": Employee(name="carpenter", wage=1.0, count=0),
            "laborer": Employee(name="laborer", wage=1.0, count=0),
        },
        "WoodenBuilding": {
            "carpenter": Employee(name="carpenter", wage=1.0, count=1000),
            "laborer": Employee(name="laborer", wage=1.0, count=2000),
        },
        "IronBuilding": {
            "ironworker": Employee(name="ironworker", wage=1.2, count=1200),
            "laborer": Employee(name="laborer", wage=1.0, count=1800),
        },
    }
    production_method: str = None

    def __init__(self, building_level: int = 0,  building_max_level: int = 0, production_method: str = "WoodenBuilding"):
        super().__init__(
            name="Construction Sector",
            build_cost=500,
            cash_reserve=0,
            building_level=building_level,
            building_max_level=building_max_level,
            production_config=self.production_methods[production_method],
            employee_config=self.employee_config[production_method]
        )
        self.production_method = production_method


class State(BaseModel):
    id: str
    buildings: List[Building]
    resources: Dict[str, Product] = {}
    export_tariff: float = 0.05

    def calculate_demand_supply(self) -> Dict[str, Dict[str, float]]:
        """Calculate total buy orders (demand) and sell orders (supply) for each product."""
        buy_orders = {}
        sell_orders = {}

        for building in self.buildings:
            for resource, quantity_needed in building.calculate_buy_orders().items():
                buy_orders[resource] = buy_orders.get(resource, 0) + quantity_needed
            for product, quantity_produced in building.calculate_sell_orders().items():
                sell_orders[product] = sell_orders.get(product, 0) + quantity_produced

        return {"buy_orders": buy_orders, "sell_orders": sell_orders}

    def update_product_prices(self):
        """Adjust product prices based on daily buy and sell orders."""
        demand_supply = self.calculate_demand_supply()
        buy_orders = demand_supply["buy_orders"]
        sell_orders = demand_supply["sell_orders"]

        for product_name, product in self.resources.items():
            product_demand = buy_orders.get(product_name, 0)
            product_supply = sell_orders.get(product_name, 0)

            # If there are no buy orders, gradually decrease the price but not below the base price
            if product_demand == 0:
                product.local_price = max(product.base_price, product.local_price * 0.98)  # Decrease slightly
            else:
                # Adjust price based on demand-supply ratio when buy orders are present
                product.adjust_price(buy_orders=product_demand, sell_orders=product_supply)

    def add_building(self, building: Building):
        """Add a building to the state and ensure resources are accounted for."""
        self.buildings.append(building)  # Treat buildings consistently as a list

        # Ensure the state's resources cover the building's consumption needs for a day
        for resource, daily_consumption in building.consumption.items():
            required_quantity = daily_consumption * building.building_level
            if resource in self.resources:
                self.resources[resource].quantity += required_quantity
            else:
                # Initialize with enough quantity to meet demand
                self.resources[resource] = Product(name=resource, base_price=0, local_price=0,
                                                   quantity=required_quantity)

    def calculate_state_production(self) -> Dict[str, float]:
        """Calculate total production for the state, adjusting for shortages."""
        total_production = {}
        for building in self.buildings:
            daily_production = building.get_daily_production()
            for product, amount in daily_production.items():
                total_production[product] = total_production.get(product, 0) + amount

        return total_production

    def allocate_resources(self) -> Dict[str, Dict[str, float]]:
        """Distribute resources to buildings proportionally based on demand."""
        total_demand = {}
        for building in self.buildings:
            for resource, quantity_needed_per_level in building.consumption.items():
                demand = quantity_needed_per_level * building.building_level
                total_demand[resource] = total_demand.get(resource, 0) + demand

        allocated_resources = {building.name: {} for building in self.buildings}
        for resource, total_available in self.resources.items():
            if total_available.quantity > 0 and resource in total_demand:
                for building in self.buildings:
                    if resource in building.consumption:
                        demand = building.consumption[resource] * building.building_level
                        allocated_quantity = (demand / total_demand[resource]) * total_available.quantity
                        allocated_resources[building.name][resource] = allocated_quantity

        return allocated_resources

    def calculate_building_productions(self) -> Dict[str, Dict[str, float]]:
        """Calculate daily production, handle resource allocation, and update finances for each building."""
        # Allocate resources for each building
        allocations = self.allocate_resources()
        self.update_product_prices()
        product_prices = {name: product for name, product in self.resources.items()}
        building_productions = {}

        for building in self.buildings:
            # Update shortage penalty based on allocated resources
            building.update_shortage_penalty(allocated_resources=allocations.get(building.name, {}))

            # Deduct consumed resources from the state
            for resource, allocated_amount in allocations.get(building.name, {}).items():
                if resource in self.resources:
                    self.resources[resource].quantity -= allocated_amount
                    self.resources[resource].quantity = max(0, self.resources[resource].quantity)

            daily_production = building.get_daily_production()
            building_productions[building.name] = daily_production

            building.print_daily_costs(product_prices)
            building.update_cash_balance(product_prices)

            for product, amount in daily_production.items():
                if product in self.resources:
                    self.resources[product].quantity += amount
                else:
                    self.resources[product] = Product(name=product, base_price=product_prices[product].base_price,
                                                      local_price=product_prices[product].local_price, quantity=amount)

        return building_productions

    def get_building_by_name(self, building_name: str) -> Optional[Building]:
        """Retrieve a building by its name from the list of buildings in the state."""
        for building in self.buildings:
            if building.name == building_name:
                return building
        return None


