import os


class GPU():
    def __init__(self, number):
        self.number = number
        self.process = [] 

    def check(self, temp=50, watt=40, memory=800, util=5, checkname=['relion', 'python']):
        if self.temp > temp:
            return False
        if self.watt > watt:
            return False
        if self.memory > memory:
            return False
        if self.util > util:
            return False

        for proc in self.process:
            for name in checkname:
                if name in proc[1]:
                    return False
       
        return True


def parse_gpus():
    gpus = {}
    os.system("nvidia-smi  > .nvidia-smi")

    with open(".nvidia-smi", 'r') as nv:
        lines = nv.readlines()

    for ind, line in enumerate(lines):
        if "NVIDIA-SMI" in line:
            driverversion = line.split()[5]
            cudaversion = line.split()[8]
        if "===" in line and "+" in line:
            dataindex = ind +1
            break

    while 'NVIDIA' in lines[dataindex]:
        num = int(lines[dataindex].split()[1])
        gpu = GPU(number=num)
        
        gpu.driver = driverversion
        gpu.cuda = cudaversion

        gpu.busid = lines[dataindex].split('|')[2].split()[0]
    
        gpu.fan = int(lines[dataindex+1].split()[1][:-1])
        gpu.temp = int(lines[dataindex+1].split()[2][:-1])
        gpu.watt = int(lines[dataindex+1].split()[4][:-1])
        gpu.maxwatt = int(lines[dataindex+1].split()[6][:-1])
        gpu.memory = int(lines[dataindex+1].split()[8][:-3])
        gpu.maxmemory = int(lines[dataindex+1].split()[10][:-3])
        gpu.util = int(lines[dataindex+1].split()[12][:-1])

        # print(gpu.number, gpu.busid, gpu.fan, gpu.temp, gpu.watt, gpu.maxwatt, gpu.memory, gpu.maxmemory, gpu.util)
        dataindex += 4
    
        gpus[int(num)] = gpu
        
    for ind, line in enumerate(lines[dataindex:]):
        if '===' in line:
            processindex = ind+1 + len(lines[:dataindex])
            break

    for line in lines[processindex:]:
        if "+-------------" in line:
            break

        gpu = line.split()[1]
        pid = line.split()[4]
        name = line.split()[6]
        memory = line.split()[7]

        gpus[int(gpu)].process.append([pid, name, memory])

    return gpus





