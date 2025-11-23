from time import perf_counter, sleep
import threading

list_1 = ['microphone', 'cup', 'TV', 'wallet', 'hat']

start = perf_counter()


def print_function():
    sleep(1)
    for i in list_1:
        print("Value:  " + i)
    print()


t1 = threading.Thread(target=print_function)
t2 = threading.Thread(target=print_function)
t3 = threading.Thread(target=print_function)
t4 = threading.Thread(target=print_function)

t1.start()
t2.start()
t3.start()
t4.start()

t1.join()
t2.join()
t3.join()
t4.join()

end = perf_counter()

print('Time to finish: {} seconds'.format(round(end-start, 2)))
