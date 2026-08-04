from time import sleep

from llm_communicator import LLMCommunicator
from google import genai
from keys import GEMINI_API_KEY


class Gemini(LLMCommunicator):
    def __init__(self, model="gemini-3.1-flash-lite", store=True,temperature=0.5):
        super().__init__(model, store, temperature)
        self.client = genai.Client(api_key = GEMINI_API_KEY)
        self.config = genai.types.GenerateContentConfig()
        self.config.temperature = self.temperature
        self.config.max_output_tokens = 10_000

    def generate_response(self, query, iteration = 0):
        """
        Sends a query to the gemini API and returns the response.
        :param query: The query to send to the gemini API.
        :param iteration: The number of iterations to send.
        :return: The response from the gemini API.
        """
        try:
            response = self.client.models.generate_content(
                model = self.model,
                contents = query,
                config = self.config
            )

        # If an error occurs, up to 5 retries are made to get a response from the model; If no response is received after 5 retries, None is returned
        # Catches Error in case the model is currently experiencing too much traffic; Automatically retries after 60 seconds
        except Exception as e:
            print(e)
            if "503 UNAVAILABLE." in str(e):
                if iteration <= 5:
                    sleep(60)
                    return self.generate_response(query, iteration)

            return None

        # Catches Error in case the model throws a "Recitation Error"; Seems to be automatic prevention system; Automatically retries after 5 seconds
        if response.text is None:
            print("Recitation Error")
            if iteration <= 5:
                sleep(5)
                return self.generate_response(query, iteration + 1)

            return None

        return response.text

