from llm_communicator import LLMCommunicator
from anthropic import Anthropic, Stream
from keys import CLAUDE_API_KEY

class Claude(LLMCommunicator):
    def __init__(self, model="claude-opus-4-6", store=True, temperature=0.5):
        super().__init__(model, store, temperature)
        self.client = Anthropic(api_key=CLAUDE_API_KEY)

    #def generate_response(self, query):
    #    """
    #    Sends a query to the claude API and returns the response.
    #    :param query: The query to send to the claude API.
    #    :return: The response from the claude API.
    #    """
    #    with self.client.messages.stream(
    #        model = self.model,
    #        max_tokens = 10_000,
    #        messages = [{"role": "user", "content": query}],
    #        temperature = self.temperature
    #    ) as stream:
    #        response = stream.get_final_message()
    #    return response.content[0].text

    def generate_response(self, query):
        """
        Sends a query to the claude API and returns the response.
        :param query: The query to send to the claude API.
        :return: The response from the claude API.
        """
        response = self.client.messages.create(
            model = self.model,
            max_tokens = 8_000,
            messages = [{"role": "user", "content": query}]
        )
        return response.content[0].text
#test = Claude()
#response = test.request("Explain how AI works in a few words")
#print(response)