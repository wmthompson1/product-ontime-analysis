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
    "Lady Juliet gazed longingly at the stars, her heart aching for Romeo. "
    "Her eyes, pools of sorrow, reflected the distant, indifferent pinpricks of light. "
    "Meanwhile, in the bustling town square, Mercutio laughed loudly with Benvolio, "
    "unaware of the anguish consuming his friend's beloved. Their easy camaraderie "
    "was a stark contrast to the secret, desperate love shared between Romeo and Juliet. "
    "A messenger, weary and dust-covered, arrived with a letter for Friar Laurence, "
    "a man known for his wisdom and willingness to help the young lovers. "
    "Hope, a fragile butterfly, fluttered in Juliet's chest as she thought of the Friar."
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
import os

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