from llm_communicator import LLMCommunicator
from google import genai
from keys import GEMINI_API_KEY

class Gemini(LLMCommunicator):
    def __init__(self, model="gemini-3-flash-preview", store=True,temperature=0.5):
        super().__init__(model, store, temperature)
        self.client = genai.Client(api_key = GEMINI_API_KEY)
        self.config = genai.types.GenerateContentConfig()
        self.config.temperature = self.temperature

    def generate_response(self, query):
        return "Placeholder response for: " + query + " (Gemini model: " + self.model + ")"
        response = self.client.models.generate_content(
            model = self.model,
            contents = query,
            config = self.config
        )
        return response.text

    def save_response(self, response):
        pass

#test = Gemini()
#response = test.request("Explain how AI works in a few words")
#print(response)

