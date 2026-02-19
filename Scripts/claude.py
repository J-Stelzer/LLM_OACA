from llm_communicator import LLMCommunicator
from anthropic import Anthropic
from keys import CLAUDE_API_KEY

class Claude(LLMCommunicator):
    def __init__(self, model="claude-opus-4", store=True, temperature=0.5):
        super().__init__(model, store, temperature)
        self.client = Anthropic(api_key=CLAUDE_API_KEY)

    def generate_response(self, query):
        response = self.client.messages.create(
            model = self.model,
            max_tokens = 150,
            messages = [{
                "role": "user",
                "content": query
            }],
        )
        return response.choices[0].message.content

    def save_response(self, response):
        pass

test = Claude()
response = test.request("Explain how AI works in a few words")
print(response)