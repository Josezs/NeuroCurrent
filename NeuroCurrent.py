#####################################
#
# Neuron structure
#   synapse (value, weight, wfactor, fmin, fmax) []
#   body (default, value)
#   output (axon) []
#
######################################

import random
import cv2
import urllib.request 
import numpy as np
import telnetlib
import time

axon_delay_cnt = [0,0]
neu_circuit = []

class c_synapse:
    def __init__(self, ax, w, t):
        self.axon = ax #the axon of the pre neuron
        self.weight = w
        self.delay = t #the delay from pre neuron cell body to the synapse
    def get_weight(self):
        return self.weight
    
class c_syn_learn_type:
    def __init__(self, tp, l_min, l_max):
        self.type_id = tp
        self.learn_min = l_min
        self.learn_max = l_max
        
class c_synapse_with_learn(c_synapse):
    def __init__(self, ax, w, t, lt, lw):
        c_synapse.__init__(self, ax, w, t)
        self.learn_type = lt
        self.learn_weight = lw
    def get_weight(self):
        return self.weight*self.learn_weight

class c_neuron:
    def __init__(self, default, value=0):
        self.body_default = default
        self.body_value = value
        self.synapse = []
        self.syn_val = []
        self.syn_w = []
        self.axon = [0]

    def activate(self):
        global axon_delay_cnt
        d_cnt = len(self.axon)
        if self.body_value < 0:
            self.axon[axon_delay_cnt[d_cnt]] = 0
        else:
            self.axon[axon_delay_cnt[d_cnt]] = self.body_value

    def integrate(self):
        self.set_syn_val()
        self.set_weight()
        self.body_value = self.body_default + np.dot(self.syn_val, self.syn_w)

    def set_syn_val(self):
        global axon_delay_cnt
        for i in range(len(self.synapse)):
            syn = self.synapse[i]
            axon_len = len(syn.axon)
            idx = axon_delay_cnt[axon_len]+syn.delay
            if idx >= axon_len:
                idx -= axon_len
            self.syn_val[i] = syn.axon[idx]

    def set_weight(self):
        for i in range(len(self.synapse)):
            syn = self.synapse[i]
            self.syn_w[i] = syn.get_weight()
            
class c_neuron_neg_pos(c_neuron):
    def __init__(self,default,value=0):
        c_neuron.__init__(self,default,value)
    def activate(self):
        global axon_delay_cnt
        d_cnt = len(self.axon)
        if self.body_value>0:
            self.axon[axon_delay_cnt[d_cnt]] = 1
        else:
            self.axon[axon_delay_cnt[d_cnt]] = -1

class c_neuron_max_pool(c_neuron):
    def __init__(self, default, value=0):
        c_neuron.__init__(self,default,value)
    def integrate(self):
        self.set_syn_val()
        maxv=0
        for v in self.syn_val:
            if v>maxv:
                maxv=v
        self.body_value=maxv
        
def add_syn(axon, post_neu, weight, axon_dly):
    post_neu.synapse.append(c_synapse(axon, weight, axon_dly))

def create_syn_vw():
    global axon_delay_cnt, neu_circuit
    max_axon_delay = len(axon_delay_cnt)-1
    for nm in neu_circuit:
        for neu in nm:
            s_cnt = len(neu.synapse)
            neu.syn_val = np.zeros((s_cnt),dtype=np.int)
            neu.syn_w = np.zeros((s_cnt),dtype=np.int)
            for syn in neu.synapse:
                max_axon_dly = len(syn.axon)
                if syn.delay > max_axon_dly:
                    for i in range(max_axon_dly, syn.delay):
                        syn.axon += [0]
                if syn.delay > max_axon_delay:
                    for i in range(max_axon_delay, syn.delay):
                        axon_delay_cnt += [0]
                    max_axon_delay = syn.delay

def activate_all():
    global neu_circuit
    for nm in neu_circuit:
        for n in nm:
            n.activate()

def run_sim(base):
    global axon_delay_cnt, neuron_circuit
    activate_all()
    for nm in neu_circuit[base:]:
        for n in nm:
            n.integrate()
    max_axon_delay = len(axon_delay_cnt)
    for i in range(2,max_axon_delay):
        axon_delay_cnt[i] += 1
        if axon_delay_cnt[i]>=i:
            axon_delay_cnt[i]=0

#Column = 320   10*32
#Row = 176 88*2 11*16

Column = 32
Row = 16


def bin_comp(comp_size, src_module, neu_module, in_base=0):
    cnt=0
    for j in range(0,comp_size-1):
        for k in range(0,comp_size-1-j):
            neu = c_neuron_neg_pos(0)
            add_syn(src_module[in_base+j].axon,neu,-1,1)
            add_syn(src_module[in_base+comp_size-1-k].axon,neu,1,1)
            neu_module += [neu]
            cnt+=1
    return cnt


def max_comp(comp_size, bin_module, max_module, in_base=0):
    cnt=0
    for j in range(0,comp_size-1):
        neu = c_neuron(-(comp_size-2))
        for k in range(0,comp_size-1-j):
            add_syn(bin_module[in_base+j*((comp_size-1)+(comp_size-1-(j-1)))//2+k].axon,neu,-1,1)
        for k in range(comp_size-1-j, comp_size-1):
            seq = k-(comp_size-1-j)+1
            add_syn(bin_module[in_base+(j-seq)*((comp_size-1)+(comp_size-1-(j-seq-1)))//2+
                               (comp_size-1-j)].axon,neu,1,1)
        max_module += [neu]
        cnt+=1
    neu = c_neuron(-(comp_size-2))
    for j in range(0,comp_size-1):
        add_syn(bin_module[in_base+j*((comp_size-1)+(comp_size-1-(j-1)))//2].axon,neu,-1,1)
    max_module += [neu]
    cnt+=1
    return cnt

def max_mask(Column, Row, src_module, max_comp_module, max_mask_module):
    cnt = 0;
    for i in range(0,Column):
        for j in range(0,Row):
            neu = c_neuron(-2000);
            add_syn(src_module[i*Row+j].axon,neu,1,3)
            add_syn(max_comp_module[i*Row+j].axon,neu,2000,1)
            max_mask_module += [neu]
            cnt+=1
    return cnt

def max_pool(src_module, src_base, size):
    neu = c_neuron(0)
    for j in range(0,size):
        add_syn(src_module[src_base+j].axon,neu,1,1)
    return neu

def max_diff(max_pool_module, cl_max_com_module, max_diff_module, size):
    cnt = 0
    for i in range(size):
        neu = c_neuron(-20000)
        mid = size//2
        if i < mid:
            weight = (mid-i)//(size//8)
        else:
            weight = (i-mid)//(size//8)
        add_syn(max_pool_module[i].axon,neu,weight,3)
        add_syn(max_pool_module[mid].axon,neu,-weight,3)
        add_syn(cl_max_comp_module[i].axon,neu,20000,1)
        max_diff_module += [neu]
        cnt += 1
    return cnt

neu_cnt=0
max_network_delay=0
sensor_module=[]
for i in range(0,Column*Row):
    neu = c_neuron(0);
    sensor_module += [neu]
    neu_cnt+=1
neu_circuit += [sensor_module]
in_neu_cnt = neu_cnt
max_network_delay+=1
'''
bin_comp_module=[]
bin_comp_cnt = neu_cnt
for i in range(0,Column):
    neu_cnt += bin_comp(Row, sensor_module, bin_comp_module, i*Row)
neu_circuit += [bin_comp_module]
bin_comp_cnt = neu_cnt-bin_comp_cnt
max_network_delay+=1

max_comp_module = []
max_comp_cnt = neu_cnt
for i in range(0,Column):
    neu_cnt += max_comp(Row,bin_comp_module, max_comp_module, i*bin_comp_cnt//Column)
neu_circuit += [max_comp_module]
max_comp_cnt=neu_cnt-max_comp_cnt
max_network_delay+=1

max_mask_cnt=neu_cnt
max_mask_module = []
neu_cnt += max_mask(Column, Row, sensor_module, max_comp_module, max_mask_module)
neu_circuit += [max_mask_module]
max_mask_cnt=neu_cnt-max_mask_cnt
max_network_delay+=1

max_pool_cnt=neu_cnt
max_pool_module = []
for i in range(0,Column):
    neu = max_pool(max_mask_module, i*Row, Row)
    max_pool_module += [neu]
    neu_cnt += 1
neu_circuit += [max_pool_module]
max_pool_cnt=neu_cnt-max_pool_cnt
max_network_delay+=1
'''
max_pool_cnt=neu_cnt
max_pool_module=[]
for i in range(Column):
    neu = c_neuron_max_pool(0)
    for j in range(0,Row):
        add_syn(sensor_module[i*Row+j].axon,neu,1,1)
    max_pool_module += [neu]
neu_circuit += [max_pool_module]
max_pool_cnt=neu_cnt-max_pool_cnt
max_network_delay+=1
    
cl_bin_comp_cnt=neu_cnt
cl_bin_comp_module=[]
neu_cnt+= bin_comp(Column, max_pool_module, cl_bin_comp_module)
neu_circuit+=[cl_bin_comp_module]
cl_bin_comp_cnt = neu_cnt-cl_bin_comp_cnt
max_network_delay+=1

cl_max_comp_cnt = neu_cnt
cl_max_comp_module = []
neu_cnt += max_comp(Column, cl_bin_comp_module, cl_max_comp_module)
neu_circuit+=[cl_max_comp_module]
cl_max_comp_cnt = neu_cnt - cl_max_comp_cnt
max_network_delay+=1
'''
average = neuron_cls(0)
for i in range(Column):
    add_syn(neuron[max_pool_base+i],average,1/Column,1)
neuron += [average]
neu_cnt+=1
'''    

cl_max_diff_cnt = neu_cnt
cl_max_diff_module = []
neu_cnt += max_diff(max_pool_module, cl_max_comp_module, cl_max_diff_module, Column)
neu_circuit += [cl_max_diff_module]
cl_max_diff_cnt = neu_cnt - cl_max_diff_cnt
max_network_delay+=1

delay_ctrl_cnt = neu_cnt
neu = c_neuron(0) 
delay_ctrl_module = [neu]
neu_cnt+=1
for i in range(0,max_network_delay):
    neu = c_neuron(0)
    add_syn(delay_ctrl_module[i].axon,neu,1,1)
    delay_ctrl_module += [neu]
    neu_cnt+= 1
delay_active = c_neuron(0)
for i in range(0,max_network_delay-1):
    add_syn(delay_ctrl_module[i].axon,delay_active,1,1)
delay_ctrl_module += [delay_active]
neu_cnt+=1
neu_circuit += [delay_ctrl_module]

left = c_neuron(0)
for i in range(0,Column//2):
    add_syn(cl_max_diff_module[i].axon,left,1,1)
neu_cnt+=1
right = c_neuron(0)
for i in range(Column//2, Column):
    add_syn(cl_max_diff_module[i].axon,right,1,1)
neu_cnt+=1
output_module =[left, right]
neu_circuit += [output_module]

create_syn_vw()

print("input:",in_neu_cnt,
#      " bin_comp:", bin_comp_cnt,
#      " max_comp:", max_comp_cnt,
#      " max_mask:", max_mask_cnt,
      " max_pool:", max_pool_cnt,"\n",
      " column_bin_comp:", cl_bin_comp_cnt,
      " column_max_comp:", cl_max_comp_cnt,
      " max_network_delay:", max_network_delay,
      " total:", neu_cnt)

tn = telnetlib.Telnet(host='192.168.8.1',port=2001)
stream=urllib.request.urlopen('http://192.168.8.1:8083/?action=stream')
tn.write(b'Hello+a 500\r\n')
tn.write(b'Hello+h 500\r\n')
bytestr=bytes()
a=b=-1
frm_counter = 0
sim_counter = 0
pimg=np.ndarray(shape=(Row,Column,3),dtype=np.uint8) 
rRow = 176//Row
rColumn = 320//Column

while True:
    while a==-1:
        bytestr+=stream.read(1024)
        a = bytestr.find(b'\xff\xd8')
        c = a
    while b==-1:
        b = bytestr.find(b'\xff\xd9',c)
        c = len(bytestr)
        if b==-1:
            bytestr+=stream.read(1024)
    jpg = bytestr[a:b+2]
    bytestr = bytestr[b+2:]
    img = cv2.imdecode(
            np.fromstring(jpg, dtype=np.uint8),
            cv2.IMREAD_COLOR)
    a=b=-1
    cv2.imshow('My original eye',img)

    if cv2.waitKey(1) ==27:
        tn.close()
        stream.close()
        exit(0) 
    if True: #frm_counter&7 == 0:
        delay_active.body_value = 1
        delay_ctrl_module[0].body_value = 1
        for i in range(0,Column):
            for j in range(0,Row):
                sensor_module[i*Row+j].body_value=img[j*rRow][i*rColumn][0]
        frm_counter+=1

    if delay_active.body_value:
        run_sim(1)
        delay_ctrl_module[0].body_value = 0
        sim_counter += 1
        if delay_ctrl_module[max_network_delay].body_value:
            value = left.body_value//8
            if (value>10):
                tn.write(b'Hello+r '+bytes(str(-value),'ascii')+b'\r\n')
            else:
                value = right.body_value//8
                if value>10:
                    tn.write(b'Hello+r '+bytes(str(value),'ascii')+b'\r\n')
            if frm_counter&31==0:
                print('lelf:', left.body_value,
                  ' right:',right.body_value,
                  ' sim cnt:',sim_counter,
                  ' frm cnt:',frm_counter)

'''
def get_syn_val(syn):
    global max_axon_delay, axon_delay_cnt
    if syn.axon_dly == 1:
        axon_ptr = axon_delay_cnt[syn.pre_neu.max_axon_dly]
    else:
        axon_ptr = axon_delay_cnt[syn.pre_neu.max_axon_dly]+syn.axon_dly-1
        if axon_ptr >= syn.pre_neu.max_axon_dly:
            axon_ptr = 0
    return syn.pre_neu.axon[axon_ptr]
        
        val = n.body_default
        for syn in n.synapse:
            syn_val = syn.get_value()
            if syn.wfactor==0:
                if syn_val>0:
                    val += syn.weight
                else:
                    val -= syn.weight
            else:
                val += syn_val*syn.weight
        n.body_value = val

'''


'''

'''

#    for j in range(Row):
#        pstr+=str(neuron[j].body_value) + ' '
#    print(pstr)

#    for i in range(Row)
#    if True:
#        i = 0
#        pcnt=0
#        for j in range(0,Row-1):
#            pstr='j:'+str(j)+' '
#            for k in range(0,Row-1-j):
#                pstr+=str(neuron[bin_comp_base+pcnt].body_value)+' '
#                pcnt+=1
#            print(pstr)
'''
    for i in range(Column):
    if True:
        i = 0
pstr='max mask row0:'
for j in range(Row):
    neu = neuron[max_mask_base+j]
    pstr+=str(neu.body_value)+' '

pstrmp='max comp row0:'
for j in range(Row):
    neu = neuron[max_comp_base+j]
    pstrmp +=str(int(neu.body_value>0))+' '

print(pstr)
print(pstrmp)

pstr='max col:'
for j in range(Column):
    neu = neuron[cl_max_comp_base+j]
    pstr+=str(int(neu.body_value>0))+' '

pstrmp='max pool:'
for j in range(Column):
    neu = neuron[max_pool_base+j]
    pstrmp+=str(neu.body_value)+' '

pstr1 = ''
neu =  neuron[max_pool_base]
syn = neu.synapse
for j in range(Row):
    pstr1 += str(syn[j].value) + ' '
print(pstr1)
#            pstr1 = 'pool syn:'
#            for j in range(Row):
#                pstr1+=str(neu.synapse[j].value)+' '
#            print(pstr1)

#            pstr='row'+str(i)+'p'+str(j)+'v:'
#            pstr+=str(neu.body_value)+':'+str(neu.body_default)+' '
#            for k in range(Row-1):
#                syn=neu.synapse[k]
#                pstr+=' '+str(syn.weight)+'v'+str(syn.value)
#        print(pstrmp)
#        print(pstr)
'''

    
    
