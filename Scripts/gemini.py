from llm_communicator import LLMCommunicator
from google import genai
from keys import GEMINI_API_KEY

class Gemini(LLMCommunicator):
    def __init__(self, model="gemini-3.1-flash-lite", store=True,temperature=0.5):
        super().__init__(model, store, temperature)
        self.client = genai.Client(api_key = GEMINI_API_KEY)
        self.config = genai.types.GenerateContentConfig()
        self.config.temperature = self.temperature

    def generate_response(self, query):
        """
        Sends a query to the gemini API and returns the response.
        :param query: The query to send to the gemini API.
        :return: The response from the gemini API.
        """
        response = self.client.models.generate_content(
            model = self.model,
            contents = query,
            config = self.config
        )
        return response.text

#test = Gemini()
#response = test.request("Explain how AI works in a few words")
#print(response)

