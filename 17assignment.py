from datetime import datetime

f = open('SP500.txt', 'r')
max_x = 0.0
count = 0
accum = 0.0

start_date = datetime(2016, 6, 1)
end_date = datetime(2017, 5, 31)
max_date = start_date

for lines in f:
   fields = lines.split(',')
   date0 = fields[0]

   # Skip the header row
   if date0 == 'Date':
      continue

      # Convert the date string to a datetime object

   date1 = datetime.strptime(date0, '%m/%d/%Y')
   #print(date1)
   if start_date <= date1 <= end_date:
      count += 1
      accum = accum + float(fields[1])

      x = float(fields[5])
      # print(x)
      if x > max_x:
         max_x = x
         max_date = date1
mean_SP = accum / count
max_interest = max_x
print(max_interest)
print(round(mean_SP, 4))
