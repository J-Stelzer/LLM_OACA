from llm_communicator import LLMCommunicator
from openai import OpenAI
from keys import CHAT_GPT_API_KEY

class ChatGPT(LLMCommunicator):
    def __init__(self, model="gpt-5-nano", store=True, temperature=0.5):
        super().__init__(model, store, temperature)
        self.client = OpenAI(api_key = CHAT_GPT_API_KEY)

    def generate_response(self, query):
        response = self.client.responses.create(
            model = self.model,
            input = query,
            store = self.store,
            temperature = self.temperature,
        )
        return response.output_text

    def save_response(self, response):
      pass


test = ChatGPT()
response = test.request("Explain how AI works in a few words")
print(response)