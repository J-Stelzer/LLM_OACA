import re

def split_response(response):
    generated_refs = response.split("\n")
    for ref in generated_refs:
        if ref.strip() and ref.startswith("R"):
            content = ref.split(" ", maxsplit=1)
            index = re.sub(r'\D', '', content[0])
            ref = content[1]
            "test".strip()
            yield {
                "index": index,
                "reference": ref
            }



#res = """R1 Caliskan, A., Bryson, J. J., & Narayanan, A. (2017). Semantics derived automatically from language corpora contain human biases. Science, 356(6334), 183–186.
#
#R2 Author, A. (Year). Title about LLMs in journalism. Journal Name, 1(1), 1–10. https://doi.org/10.0000/placeholder2
#
#R3 Author, B. (Year). Title about LLMs in copywriting. Journal Name, 2(1), 11–22. https://doi.org/10.0000/placeholder3
#
#R4 Author, C. (Year). Title about LLMs in academia. Journal Name, 3(1), 23–34. https://doi.org/10.0000/placeholder4
#
#R5 Author, D. (Year). Title about other writing tasks. Journal Name, 4(1), 35–46. https://doi.org/10.0000/placeholder5
#
#R6 OpenAI. (2023). ChatGPT: A language model accessible to the public. OpenAI Blog. https://openai.com/blog/chatgpt
#
#R7 Bartlett, F. C. (1932). Remembering: A study in experimental and social psychology. Cambridge, England: Cambridge University Press.
#
#R8 Boyd, R., & Richerson, P. J. (1985). Culture and the Evolutionary Process. Chicago, IL: University of Chicago Press.
#
#R9 Mesoudi, A. (2011). Cultural evolution: A review of the field. Trends in Cognitive Sciences, 15(6), 246–251.
#
#R10 Author, E. (Year). Transmission chain experiments in psychology: A methodological overview. Journal of Experimental Psychology: General, 110(2), 200–215.
#
#R11 Baumeister, R. F., Bratslavsky, E., Finkenauer, C., & Vohs, K. D. (2001). Bad is stronger than good. American Psychologist, 56(3), 323–329.
#"""
#
#print(list(split_response(res)))