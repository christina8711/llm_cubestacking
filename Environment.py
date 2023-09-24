from __future__ import annotations

import copy
import re
from abc import ABC, abstractmethod
from random import shuffle
from typing import List

import numpy as np


class PreConditionException(Exception):
    pass


class PostConditionException(Exception):
    pass


class FailedSimulationException(Exception):
    pass


class StateFactory:

    def __init__(self, nr_stacks: int, nr_cubes: int):
        self.nr_stacks = nr_stacks
        self.nr_cubes = nr_cubes

    def generate_state(self):
        cubes = [i for i in range(self.nr_cubes)]
        shuffle(cubes)

        state = [[] for _ in range(self.nr_stacks)]
        # Based on: https://stackoverflow.com/questions/56913839/randomly-split-data-in-n-groups
        for cube in cubes:  # spread the remaining
            state[np.random.randint(self.nr_stacks)].append(cube)
        return state


class Arm:

    def __init__(self, cube: int = None):
        self.cube = cube

    def __eq__(self, other):
        return self.cube == other.cube

    def holding(self, x: int) -> bool:
        """
        Returns true if and only if the robot arm is holding cube x.
        :param x:
        :return:
        """
        return self.cube == x

    def empty(self) -> bool:
        """
        Returns true if and only if the robot arm is not holding a cube.
        :return:
        """
        return self.cube is None


class State:

    def __init__(self, stacks: List[List[int]]):
        self.stacks = stacks
        self.arm = Arm()

    @staticmethod
    def from_description(descriptions: List[str]) -> State:
        on_table_descriptions = list(filter(lambda x: x.startswith("OnTable("), descriptions))
        on_descriptions = list(filter(lambda x: x.startswith("On("), descriptions))

        stacks = []
        for on_table_description in on_table_descriptions:
            on_table = OnTable.parse(on_table_description)
            stacks.append([on_table.x])

        state = State(stacks)

        for on_descriptions in on_descriptions:
            on = On.parse(on_descriptions)
            stack_index = state.find_stack(on.y)
            state.add_cube_to_stack(stack_index, on.x)

        # TODO: Clear, ArmEmpty, Holding

        return state

    def __eq__(self, other):
        return self.stacks == other.stacks and self.arm == other.arm

    def find_stack(self, x: int) -> int:
        for i in range(len(self.stacks)):
            stack = self.stacks[i]
            for j in range(len(stack)):
                y = stack[j]
                if x == y:
                    return i
        raise Exception("Cube not found.")

    def find_empty_stack(self) -> int:
        for i in range(len(self.stacks)):
            stack = self.stacks[i]
            if len(stack) == 0:
                return i
        raise Exception("No empty stack found.")

    def add_cube_to_stack(self, stack_index: int, x: int):
        for i in range(len(self.stacks)):
            if i == stack_index:
                stack = self.stacks[i]
                stack.append(x)

    def remove_cube(self, x: int):
        for i in range(len(self.stacks)):
            stack = self.stacks[i]
            if x in stack:
                stack.remove(x)

    def clear(self, x: int) -> bool:
        """
        Returns true if and only if there is no cube on top of cube x.
        :param x:
        :return:
        """
        for i in range(len(self.stacks)):
            stack = self.stacks[i]
            if stack[-1] == x:
                return True
        return False

    def on_table(self, x: int) -> bool:
        """
        Returns true if and only if cube x is on the table.
        :param x:
        :return:
        """
        for i in range(len(self.stacks)):
            stack = self.stacks[i]
            if stack[0] == x:
                return True
        return False

    def on(self, x: int, y: int) -> bool:
        """
        Returns true if and only if cube x is on top of cube y.
        :param x:
        :param y:
        :return:
        """
        for i in range(len(self.stacks)):
            stack = self.stacks[i]
            for j in range(len(stack)):
                if stack[j] == x:
                    assert j - 1 >= 0
                    return stack[j - 1] == y
        return False

    def to_string(self) -> str:
        raise NotImplementedError()

    def to_json(self):
        raise NotImplementedError()


class Action(ABC):

    @staticmethod
    def parse(step: str) -> Action:
        if step.startswith("Stack"):
            return Stack.parse(step)
        elif step.startswith("Unstack"):
            return Unstack.parse(step)
        elif step.startswith("Pickup"):
            return Pickup.parse(step)
        elif step.startswith("Putdown"):
            return Putdown.parse(step)
        raise Exception("Unknown action.")

    @staticmethod
    @abstractmethod
    def to_regex() -> str:
        pass

    @abstractmethod
    def simulate(self, state: State) -> State:
        pass


class Ontology(ABC):

    @staticmethod
    @abstractmethod
    def parse(descriptions: List[str]) -> Ontology:
        pass


class On(Ontology):

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    @staticmethod
    def parse(description: str) -> On:
        regex = re.compile('On\((\d+),\s*(\d+)\)')
        arguments = regex.findall(description)
        return On(*map(lambda x: int(x), arguments[0]))


class OnTable(Ontology):

    def __init__(self, x: int):
        self.x = x

    @staticmethod
    def parse(description: str) -> OnTable:
        regex = re.compile('OnTable\((\d+)\)')
        arguments = regex.findall(description)
        return OnTable(*map(lambda x: int(x), arguments[0]))


class Clear(Ontology):

    def __init__(self, x: int):
        self.x = x

    @staticmethod
    def parse(description: str) -> Clear:
        regex = re.compile('Clear\((\d+)\)')
        arguments = regex.findall(description)
        return Clear(*map(lambda x: int(x), arguments[0]))


class Holding(Ontology):

    def __init__(self, x: int):
        self.x = x

    @staticmethod
    def parse(description: str) -> Holding:
        regex = re.compile('Holding\((\d+)\)')
        arguments = regex.findall(description)
        return Holding(*map(lambda x: int(x), arguments[0]))


class ArmEmpty(Ontology):

    def __init__(self):
        pass

    @staticmethod
    def parse(description: str) -> ArmEmpty:
        return ArmEmpty()


class Stack(Action):

    def __init__(self, x: int, y: int):
        """
        Stacks cube x on cube y.
        'name': 'Stack(x, y)',
        'preconditions': ['Clear(y)', 'Holding(x)'],
        'add_effects': ['ArmEmpty', 'On(x, y)', 'Clear(x)'],
        'delete_effects': ['Clear(y)', 'Holding(x)'],
        'constraints': ['x != y', 'x != Table', 'y != Table']
        :param x:
        :param y:
        """
        self.x = x
        self.y = y

    @staticmethod
    def parse(step: str) -> Action:
        regex = re.compile('Stack\((\d+),\s*(\d+)\)')
        arguments = regex.findall(step)
        return Stack(*map(lambda x: int(x), arguments[0]))

    def to_string(self):
        raise NotImplementedError()

    @staticmethod
    def to_regex() -> str:
        return 'Stack\(\d+,\s*\d+\)'

    def simulate(self, state: State) -> State:

        # Check pre-condition
        if not state.clear(self.y):
            raise PreConditionException("{} must be clear.".format(self.y))

        # Check pre-condition
        if not state.arm.holding(self.x):
            raise PreConditionException("{} must be held by arm.".format(self.x))

        # Effects
        state = copy.deepcopy(state)
        state.remove_cube(self.x)
        new_stack_index = state.find_stack(self.y)
        state.add_cube_to_stack(new_stack_index, self.x)

        # Check post-condition
        if not state.arm.empty():
            raise PreConditionException("Arm must be empty.")

        # Check post-condition
        if not state.on(self.x, self.y):
            raise PreConditionException("{} must be on {}.".format(self.x, self.y))

        # Check post-condition
        if not state.clear(self.x):
            raise PreConditionException("{} must be clear.".format(self.x))

        return state


class Unstack(Action):

    def __init__(self, x: int, y: int):
        """
        'name': 'Unstack(x, y)',
        'preconditions': ['On(x,y)', 'Clear(x)', 'ArmEmpty()'],
        'add_effects': ['Holding(x)', 'Clear(y)'],
        'delete_effects': ['On(x,y)', 'Clear(x)', 'ArmEmpty()'],
        'constraints': ['x != y', 'x != Table', 'y != Table']
        :param x:
        :param y:
        """
        self.x = x
        self.y = y

    @staticmethod
    def parse(step: str) -> Action:
        regex = re.compile('Unstack\((\d+),\s*(\d+)\)')
        arguments = regex.findall(step)
        return Unstack(*map(lambda x: int(x), arguments[0]))

    def to_string(self):
        raise NotImplementedError()

    @staticmethod
    def to_regex() -> str:
        return 'Unstack\(\d+,\s*\d+\)'

    def simulate(self, state: State) -> State:

        # Check pre-condition
        if not state.on(self.x, self.y):
            raise PreConditionException("{} must be on {}.".format(self.x, self.y))

        # Check pre-condition
        if not state.clear(self.x):
            raise PreConditionException("{} must be clear.".format(self.x))

        # Check pre-condition
        if not state.arm.empty():
            raise PreConditionException("Arm must be empty.")

        # Effects
        state = copy.deepcopy(state)
        state.arm = Arm(self.x)
        state.remove_cube(self.x)

        # Check post-condition
        if not state.arm.holding(self.x):
            raise PreConditionException("{} must be held by arm.".format(self.x))

        # Check post-condition
        if not state.clear(self.y):
            raise PreConditionException("{} must be clear.".format(self.y))

        return state


class Pickup(Action):

    def __init__(self, x: int):
        self.x = x

    @staticmethod
    def parse(step: str) -> Action:
        regex = re.compile('Pickup\((\d+)\)')
        arguments = regex.findall(step)
        return Pickup(*map(lambda x: int(x), arguments[0]))

    def to_string(self):
        raise NotImplementedError()

    @staticmethod
    def to_regex() -> str:
        return 'Pickup\(\d+\)'

    def simulate(self, state: State) -> State:

        # Check pre-condition
        if not state.on_table(self.x):
            raise PreConditionException("{} must be on table.".format(self.x))

        # Check pre-condition
        if not state.clear(self.x):
            raise PreConditionException("{} must be clear.".format(self.x))

        # Check pre-condition
        if not state.arm.empty():
            raise PreConditionException("Arm must be empty.")

        # Effects
        state = copy.deepcopy(state)
        state.arm = Arm(self.x)
        state.remove_cube(self.x)

        # Check post-condition
        if not state.arm.holding(self.x):
            raise PreConditionException("{} must be held by arm.".format(self.x))

        return state


class Putdown(Action):

    def __init__(self, x: int):
        self.x = x

    @staticmethod
    def parse(step: str) -> Action:
        regex = re.compile('Putdown\((\d+)\)')
        arguments = regex.findall(step)
        return Putdown(*map(lambda x: int(x), arguments[0]))

    def to_string(self):
        raise NotImplementedError()

    @staticmethod
    def to_regex() -> str:
        return 'Putdown\(\d+\)'

    def simulate(self, state: State) -> State:

        # Check pre-condition
        if not state.arm.holding(self.x):
            raise PreConditionException("{} must be held by arm.".format(self.x))

        # Effects
        state = copy.deepcopy(state)
        stack_index = state.find_empty_stack()
        state.add_cube_to_stack(stack_index, self.x)
        state.arm = Arm()

        # Check post-condition
        if not state.on_table(self.x):
            raise PreConditionException("{} must be on table.".format(self.x))

        # Check post-condition
        if not state.arm.empty():
            raise PreConditionException("Arm must be empty.")

        # Check post-condition
        if not state.clear(self.x):
            raise PreConditionException("{} must be clear.".format(self.x))

        return state


class Environment:

    def __init__(self, ontology, initial_state, goal_state):
        self.ontology = ontology
        self.initial_state = initial_state
        self.goal_state = goal_state

    def to_json(self):
        raise NotImplementedError()

    def simulate(self, response: str):
        actions = [Stack, Unstack, Pickup, Putdown]
        action_regex = "|".join(map(lambda x: x.to_regex(), actions))
        regex = re.compile('\d+\.\s+(' + action_regex + ')\s*')
        steps = regex.findall(response)

        state = self.initial_state

        for step in steps:
            action = Action.parse(step)
            state = action.simulate(state)

        if state != self.goal_state:
            raise Exception("Goal state does not match.")
