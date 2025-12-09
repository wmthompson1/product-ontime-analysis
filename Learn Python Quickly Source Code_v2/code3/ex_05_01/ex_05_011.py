import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Load the model and tokenizer
model = AutoModelForCausalLM.from_pretrained("gpt2")
tokenizer = AutoTokenizer.from_pretrained("gpt2")

# Define the input prompt
prompt = "Hello, how are you?"

# Generate text one token at a time
input_ids = tokenizer.encode(prompt, return_tensors="pt")
for i in range(10):
    outputs = model(input_ids)
    logits = outputs.logits[:, -1, :]
    probs = torch.softmax(logits, dim=-1)
    next_token_id = torch.argmax(probs)
    input_ids = torch.cat((input_ids, next_token_id.unsqueeze(0).unsqueeze(0)), dim=1)

# Print the generated text
print(tokenizer.decode(input_ids[0], skip_special_tokens=True))
