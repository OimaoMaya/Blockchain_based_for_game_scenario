import subprocess
import time

# node numbers
num_nodes = 10

# Use loop to open terminal for 10 nodes
for i in range(num_nodes):
    command = 'python node{}.py'.format(i + 1)
    # dela between every node
    time.sleep(1)
    subprocess.Popen(['start', 'cmd', '/k', command], shell=True)