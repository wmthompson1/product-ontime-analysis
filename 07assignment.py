from datetime import datetime

f = open('SP500.txt', 'r')
max_x = 0

for lines in f:
   fields = lines.split(',')
   date0 = fields[0]
   
   # Skip the header row
   if date0 == 'Date':
       continue
       
   date1 = datetime.strptime(date0, '%m/%d/%Y')
   print(date1)
