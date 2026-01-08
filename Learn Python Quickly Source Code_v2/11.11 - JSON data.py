
import json

sample_json = '{"Name": "Jenna", "Friends": ["Laura", "Dave"]}'
samples_dict = json.loads(sample_json)

print(samples_dict['Friends'])

computer_dict = {'Drink:': 'Coffee, Juice',
                 'Price': '$3.00, $4.00', 'Container': 'Bottle, Mug'}
computer_json = json.dumps(computer_dict)

with open('computer.txt', 'w') as json_file:
    json.dump(computer_dict, json_file)

with open('computer.txt', 'r') as j:
    loaded_data = json.load(j)
    print(loaded_data)
