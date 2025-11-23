sh = input('Enter Hours: ')
sr = input("Enter Rate: ")


try:
    fh = float(sh)
    fr = float(sr)
    
except:
    print('Error, please enter numeric type.')
    quit()
    
if fh > 40:
    reg = 40 * fr
    ot = ((fh-40) * fr) * 1.5
    tot = reg + ot
else:
     reg = fr * fh
print ("tot", tot)