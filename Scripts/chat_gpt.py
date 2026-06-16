from llm_communicator import LLMCommunicator
from openai import OpenAI
from keys import CHAT_GPT_API_KEY

class ChatGPT(LLMCommunicator):
    def __init__(self, model="gpt-5.2", store=True, temperature=0.5):
        super().__init__(model, store, temperature)
        self.client = OpenAI(api_key = CHAT_GPT_API_KEY)

    def generate_response(self, query):
        """
        Sends a query to the chatGPT API and returns the response.
        :param query: The query to send to the chatGPT API.
        :return: The response from the chatGPT API.
        """
        response = self.client.responses.create(
            model = self.model,
            input = query,
            store = self.store,
            max_output_tokens = 10_000,
            temperature = self.temperature
        )
        return response.output_text


#test = ChatGPT()
#response = test.request("Explain how AI works in a few words")
#print(response)