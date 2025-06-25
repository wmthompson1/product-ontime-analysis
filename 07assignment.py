from datetime import datetime

f = open('SP500.txt', 'r')
max_x = 0

for lines in f:
   start_date = datetime(2016, 6, 1)
   end_date = datetime(2016, 12, 31)

   parsed_date = lines[0]
   date1 = datetime.date(parsed_date)
   print(date1)
   if start_date <= date <= end_date:
      max_x = lines[6]
      print(max_x)

   print(lines.strip())
#itm = lines[1]
#max_x = lines[6]
