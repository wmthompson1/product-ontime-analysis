import re

search_pattern = re.compile(r'\d')
search_pattern1 = re.compile(r'\d\d\d')
search_pattern2 = re.compile(r'\d\d\d-\d\d\d-\d\d\d\d')
search_pattern3 = re.compile(r'\d{3}-\d{3}-\d{4}')
search_pattern4 = re.compile(r'[A-Z]+[A-Z]{0,4}')
search_pattern5 = re.compile(r'[A-Z]')

target_text = "Learning Python can be challenging, but the more you practice the better you'll get. " \
              "Look at how far you've come already. You used to know nothing, but now you know a lot in comparison. " \
              "While there's still so much more for you to learn, you can do it if you persevere. " \
              "--- 1 2 3 4 5 6 7 8 9 10. 123-456-7890. Here's the thing we want to SEARCH."

# The finditer method
matched_text = search_pattern.finditer(target_text)
for m in matched_text:
    print(m)

matched_text = search_pattern1.finditer(target_text)
for m in matched_text:
    print(m)

matched_text = search_pattern2.finditer(target_text)
for m in matched_text:
    print(m)

matched_text = search_pattern3.finditer(target_text)
for m in matched_text:
    print(m)

matched_text = search_pattern4.finditer(target_text)
for m in matched_text:
    print(m)

matched_text = search_pattern5.finditer(target_text)
for m in matched_text:
    print(m)
