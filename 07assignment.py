from datetime import datetime

f = open('SP500.txt', 'r')
max_x = 0.0

start_date = datetime(2016, 1, 1)
end_date = datetime(2017, 12, 31)

for lines in f:
   fields = lines.split(',')
   date0 = fields[0]

   # Skip the header row
   if date0 == 'Date':
      continue

      # Convert the date string to a datetime object

   date1 = datetime.strptime(date0, '%m/%d/%Y')
   #print(date1)
   if start_date >= date1 <= end_date:
      x = float(fields[1])
      print(x)
      if x > max_x:
         max_x = x
         max_date = date1
         print(max_x, max_date)
