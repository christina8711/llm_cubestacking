import openai  # Import the OpenAI library
import json  # Import the JSON library for handling configuration

from Environment import Environment


class CubeStackingAssistant:
    # Import OpenAI API Key
    def __init__(self, config_file='config.json'):
        self.api_key = self.load_api_key(config_file)

    def load_api_key(self, config_file):
        try:
            with open(config_file, 'r') as config_file:
                config = json.load(config_file)
                return config.get('api_key', '')
        except FileNotFoundError:
            print(f"Config file '{config_file}' not found.")
            return ''

    def chat_with_assistant(self, conversation_log):
        # Use OPENAI's API to chat with the ChatGPT-4 assistant
        openai.api_key = self.api_key  # Set the API key
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Using the GPT-4 version
            messages=conversation_log,
        )

        # Extract and append the assistant's reply to the conversation
        assistant_reply = response.choices[0].message.content.strip()
        conversation_log.append(
            {'role': 'assistant', 'content': assistant_reply})

    def perform_strips_planning(self, ontology, initial_state, goal_state, actions):
        # Create an initial conversation log
        conversation_log = [
            {'role': 'system', 'content': 'Let\'s perform STRIPS Planning.'}]

        # Provide context about ontology, current state, and goal
        conversation_log.append({'role': 'user', 'content': 'My world contains a robot arm with a gripper, 3 blocks of equal size (A,B, and C), and a table-top. Some domain constraints is that only one block can be directly on top of another, any number of blocks can be on the table and the robot arm with a gripper can only hold one block at a time. Before we start, let me define our formal language terms and ontology.'})

        # Define ontology
        for term in ontology:
            conversation_log.append({'role': 'user', 'content': term})

        # Describe the current state of the environment
        conversation_log.append(
            {'role': 'user', 'content': 'Here is the current state of the environment:'})
        for fact in initial_state:
            conversation_log.append({'role': 'user', 'content': fact})

        # Describe the goal state
        conversation_log.append(
            {'role': 'user', 'content': 'Here is the goal state:'})
        for fact in goal_state:
            conversation_log.append({'role': 'user', 'content': fact})

        # Describe the available actions
        conversation_log.append(
            {'role': 'user', 'content': 'Here are the available actions:'})
        for action in actions:
            # Convert the 'constraints' list to a string
            constraints_str = ', '.join(action['constraints'])
            action_description = f"{action['name']}:\n- Preconditions: {', '.join(action['preconditions'])}\n- Add: {', '.join(action['add_effects'])}\n- Delete: {', '.join(action['delete_effects'])}\n- Constraints: {constraints_str}"
            conversation_log.append(
                {'role': 'user', 'content': action_description})

        # Request assistance for STRIPS Planning
        # conversation_log.append({'role': 'user', 'content': 'Please provide the most optimized sequence of action operations to go from the initial state to the goal state. Also, please provide the updated lists (perform, preconditions, add, delete, constraints) for each action.'})
        conversation_log.append(
            {'role': 'user', 'content': 'Please provide a sequence of actions to go from the initial state to the goal state using only the actions described above.'})

        # Start the conversation with the assistant
        self.chat_with_assistant(conversation_log)

        # Extract the assistant's responses
        assistant_responses = [message['content']
                               for message in conversation_log if message['role'] == 'assistant']

        return assistant_responses


if __name__ == "__main__":

    api_key = 'config.json'
    test_agent = CubeStackingAssistant(api_key)

    # Define your ontology, initial state, goal state, and actions
    ontology = [
        "On(x, y): means block x is on top of block y. ",
        "OnTable(x): means x is on the table.",
        "Clear(x): means nothing is on top of block x.",
        "Holding(x): means robot arm is holding block x. ",
        "ArmEmpty(): means Robot arm/hand is not holding anything ( in terms of the blocks in the environment).",
        "ClosedWorldAssumption():means anything not stated is assumed to be false"
    ]

    # initial_state = ["OnTable(C)", "On(B,C)", "On(A,B)",
    #                  "Clear(A)", "OnTable(D)", "On(E,D)", "ArmEmpty()"]  # Arbitrary Parameters
    #
    # goal_state = ["OnTable(A)", "On(B,A)", "Clear(B)",
    #               "OnTable(C)", "On(D,C)", "Clear(D)", "OnTable(E)", "Clear(E)", "ArmEmpty()"]  # Arbitrary Parameters

    initial_state = ["OnTable(A)", "On(B,A)", "Clear(B)", "OnTable(C)", "On(D,C)", "Clear(D)",
                     "OnTable(E)", "Clear(E)", "OnTable(F)", "Clear(F)", "Holding(G)"]  # Arbitrary Parameters

    goal_state = ["OnTable(D)", "On(E,D)", "On(F,E)", "Clear(F)", "OnTable(G)", "On(A,G)",
                  "Clear(A)", "OnTable(B)", "Clear(B)", "OnTable(C)", "Clear(C)" "ArmEmpty()"]  # Arbitrary Parameters

    actions = [
        # Define actions here
        {
            'name': 'Stack(x, y)',
            'preconditions': ['Clear(y)', 'Holding(x)'],
            'add_effects': ['ArmEmpty', 'On(x, y)', 'Clear(x)'],
            'delete_effects': ['Clear(y)', 'Holding(x)'],
            'constraints': ['x != y', 'x != Table', 'y != Table']
        },
        {
            'name': 'Unstack(x, y)',
            'preconditions': ['On(x,y)', 'Clear(x)', 'ArmEmpty()'],
            'add_effects': ['Holding(x)', 'Clear(y)'],
            'delete_effects': ['On(x,y)', 'Clear(x)', 'ArmEmpty()'],
            'constraints': ['x != y', 'x != Table', 'y != Table']
        },
        {
            'name': 'Pickup(x)',
            'preconditions': ['OnTable(x)', 'Clear(x)', 'ArmEmpty()'],
            'add_effects': ['Holding(x)'],
            'delete_effects': ['OnTable(x)', 'Clear(x)', 'ArmEmpty()'],
            'constraints': ['x != Table']
        },
        {
            'name': 'Putdown(x)',
            'preconditions': ['Holding(x)'],
            'add_effects': ['OnTable(x)', 'ArmEmpty()', 'Clear(x)'],
            'delete_effects': ['Holding(x)'],
            'constraints': ['x != Table']
        }
    ]

    # Perform STRIPS Planning
    plan = test_agent.perform_strips_planning(
        ontology, initial_state, goal_state, actions)

    # Print the assistant's responses
    for response in plan:
        print(response)

    response = plan[0]

    environment = Environment(ontology, initial_state, goal_state)
    environment.simulate(response)
