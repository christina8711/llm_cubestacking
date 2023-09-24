import unittest

from Environment import Environment, FailedSimulationException, State


class MyTestCase(unittest.TestCase):

    ontology = [
        "On(x, y): means block x is on top of block y. ",
        "OnTable(x): means x is on the table.",
        "Clear(x): means nothing is on top of block x.",
        "Holding(x): means robot arm is holding block x. ",
        "ArmEmpty(): means Robot arm/hand is not holding anything ( in terms of the blocks in the environment).",
        "ClosedWorldAssumption():means anything not stated is assumed to be false"
    ]

    def test_something(self):

        response = """
        1. Unstack(1, 2)
        2. Putdown(1)
        3. Pickup(2)
        4. Stack(2, 1)
        5. Unstack(3, 2)
        6. Putdown(3)
        7. Pickup(4)
        8. Stack(4, 3)
        9. Putdown(4)
        10. Pickup(5)
        11. Putdown(5)
        """

        initial_state_descriptions = ["OnTable(3)", "On(2, 3)", "On(1, 2)",
                         "Clear(1)", "OnTable(4)", "On(5, 4)", "ArmEmpty()"]

        goal_state_descriptions = ["OnTable(1)", "On(2, 1)", "Clear(2)",
                      "OnTable(3)", "On(4, 3)", "Clear(4)", "OnTable(5)", "Clear(5)",
                      "ArmEmpty()"]

        initial_state = State.from_description(initial_state_descriptions)
        goal_state = State.from_description(goal_state_descriptions)

        environment = Environment(self.ontology, initial_state, goal_state)

        # Based on: https://stackoverflow.com/questions/6181555/pass-a-python-unittest-if-an-exception-isnt-raised
        raised = False
        try:
            environment.simulate(response)
        except FailedSimulationException:
            raised = True
        self.assertFalse(raised, "Exception raised")


if __name__ == '__main__':
    unittest.main()
