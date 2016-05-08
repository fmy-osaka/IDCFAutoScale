import sys
 
r = open(sys.argv[1], 'rb') 
f = open('/home/td-agent-python/out_exec.log', 'ab')
strList = r.readlines()
  
for line in strList:
    f.write(line)
 
f.close()