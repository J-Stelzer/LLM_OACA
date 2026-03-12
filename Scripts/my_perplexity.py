from llm_communicator import LLMCommunicator
import perplexity as perp
from keys import PERPLEXITY_API_KEY

class Perplexity(LLMCommunicator):
    def __init__(self, model="sonar-pro", store=True, temperature=0.5):
        super().__init__(model, store, temperature)
        self.client = perp.Perplexity(api_key = PERPLEXITY_API_KEY)

    def generate_response(self, query):
        response = self.client.chat.completions.create(
            model = self.model,
            messages = [{"role": "user", "content": query}]
        )
        return response.choices[0].message.content

    def save_response(self, response):
        pass


#test = Perplexity()
#response = test.request("Explain how AI works in a few words")
#print(response)