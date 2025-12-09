sScore = input('Enter Score: ')

try:
    fScore = float(sScore)
    if fScore > 1.0:
       errx = 2
    elif fScore < 0:
       errx = 2
    elif fScore >= 0.0 and fScore <= 1.0:
        errx = 0
        if fScore >= .9:
            g = 'A'
        elif fScore >= .8:
            g = 'B'
        elif fScore >= .7:
            g = 'C'
        elif fScore >= .6:
            g = 'D'
        elif fScore < .6:
            g = 'F'
except:
    print('Error, please enter numeric type.')
    quit()
if errx > 1:
    print("Please enter a score between 0 and 1")
    quit()
print(g)