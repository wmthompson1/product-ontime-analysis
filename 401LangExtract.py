import textwrap
import langextract as lx
import os

from dotenv import load_dotenv

load_dotenv()

# 1. Define a concise prompt
prompt = textwrap.dedent("""\
Extract characters, emotions, and relationships in order of appearance.
Use exact text for extractions. Do not paraphrase or overlap entities.
Provide meaningful attributes for each entity to add context.""")

# 2. Provide a high-quality example to guide the model
examples = [
    lx.data.ExampleData(
        text=("ROMEO. But soft! What light through yonder window breaks? It is"
              " the east, and Juliet is the sun."),
        extractions=[
            lx.data.Extraction(
                extraction_class="character",
                extraction_text="ROMEO",
                attributes={"emotional_state": "wonder"},
            ),
            lx.data.Extraction(
                extraction_class="emotion",
                extraction_text="But soft!",
                attributes={"feeling": "gentle awe"},
            ),
            lx.data.Extraction(
                extraction_class="relationship",
                extraction_text="Juliet is the sun",
                attributes={"type": "metaphor"},
            ),
        ],
    )
]

# 3. Run the extraction on your input text
input_text = (
    "Molly is my wife. I love her dearly, and I smile when I think of her. "
    "She has a heart full of love, and she is the sun that warms my life. "
    "She makes me happy, and she is very funny so she makes me laugh. "
    "I rub her back and she always reacts, she is reacting to life at the same time. " 
    "She is a very good wife and she is the best wife in the world. "

)
# Used to securely store your API key
##from google.colab import userdata

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
result = lx.extract(
    text_or_documents=input_text,
    prompt_description=prompt,
    examples=examples,
    model_id="gemini-2.5-pro",
    api_key=GOOGLE_API_KEY,
)
#import os

# Save the results to a JSONL file
output_filename = "extraction_results.jsonl"
lx.io.save_annotated_documents([result], output_name=output_filename)

# Define potential åfile paths
file_paths_to_check = [output_filename, os.path.join("test_output", output_filename)]

found_file = False
for file_path in file_paths_to_check:
    if os.path.exists(file_path):
        print(f"Found file at: {file_path}")
        # Generate the interactive visualization from the file
        html_content_obj = lx.visualize(file_path)
        print("Content of html_content_obj object:")
        print(html_content_obj) # Print the object itself
        # Get the HTML string representation using _repr_html_()
        # Check if it's an object with _repr_html_ method or already a string
        if hasattr(html_content_obj, '_repr_html_'):
            html_string = html_content_obj._repr_html_()
        else:
            html_string = str(html_content_obj)
        print("HTML string obtained via _repr_html_():")
        print(html_string) # Print the obtained HTML string

        with open("visualization.html", "w") as f:
            f.write(html_string)  # Write the HTML string
        print("Visualization saved to visualization.html")
        found_file = True
        break

if not found_file:
    print(f"Error: {output_filename} was not found in expected locations.")