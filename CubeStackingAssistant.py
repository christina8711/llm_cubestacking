import openai  # Import the OpenAI library


class CubeStackingAssistant:
    # Import OpenAI API Key
    def __init__(self, api_key='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'):
        self.api_key = api_key

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
