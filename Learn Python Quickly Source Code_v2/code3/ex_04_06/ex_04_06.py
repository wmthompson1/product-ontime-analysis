'''
Use 45 hours and a rate of 10.50 per hour 
to test the program (the pay should be 498.75).
'''
from datetime import datetime
today = datetime.now()
formatted_date = f"Today's date is {today:%B %d, %Y}"
print(formatted_date)  # Output: Today's date is October 05, 2023 (or current date)

"""You can also use similar shorthand for other operations:"""
x = 1
x += 1 #(equivalent to x = x + 1)
x *= 2 #(equivalent to x = x * 2)
x /= 2 #(equivalent to x = x / 2)
print(f"Learning about f strings {x}")

def computepay(fh, fr):
    if fh > 40:
        reg = 40 * fr
        ot = ((fh-40) * fr) * 1.5
        tot = reg + ot
    else:
        reg = fr * fh
    return tot

hrs = float(input("Enter Hours:"))
rat = float(input("Enter Rate:"))
p = computepay(hrs, rat)
print("Pay", p)

