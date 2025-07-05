import nltk

nltk.download('punkt')
nltk.download('punkt_tab')

text = "I can't wait to build AI applications"
tokens = nltk.word_tokenize(text)
print(tokens)
