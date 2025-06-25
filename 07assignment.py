import datetime

f = open('SP500.txt','r')
max_x = 0

for lines in f:
   print(lines.strip())
   #itm = lines[1]
   #max_x = lines[6]