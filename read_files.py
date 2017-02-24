#-*- coding: utf-8 -*-

import os, sys
import  Tkinter
from functools import partial
import re

gFileInfos=[]



class FileInfo(object):
    def __init__(self, name , segs):
        self.name=name;
        self.segments=[]
        ofs=0;
        for s in segs:
            size=s[1]-s[0]            
            self.segments.append([s[0], s[1], size, ofs])
            ofs+=size                    
            self.start_blk=segs[0][0]
            self.end_blk=segs[-1:][0][1]
    def may_match(self,blk):
        return True
    def match_precise(self,blk):
        for seg in self.segments:
            if(seg[0]<= blk <=seg[1]):
                return [self.name, seg[3]+blk-seg[0]]

def parse_one_line(line):
    pat= re.match('(/[system|data|misc]\S*)\s+(\d+\s+\d+)+', line)
    if  pat == None:
        print line;
    filename=pat.group(1)
    strs = re.findall('\d+\s+\d+',line)
    segments=[]
    for s in strs:
        start=int(re.match('(\d+)\s+(\d+)', s).group(1))
        end=int(re.match('(\d+)\s+(\d+)', s).group(2))
        segments.append([start,end])     
    return FileInfo(filename, segments)
    
def read_into_map(input, infos):    
    print "块号文件绝对路径", input.get()
    f = open(input.get())
    lines=f.readlines()    
    f.close()
    for line in lines:
        infos.append(parse_one_line(line))
        
def process_file(input, infos):   
    read_into_map(input, infos)
    input.set("完成提取")    
    
def inquiry_by_blk(blk, infos):
    for inf in infos:
        if(inf.may_match(blk)):
            mat=inf.match_precise(blk)            
            if mat:
                return mat
               
def inquiry_file(input, infos ):
    str=input.get()
    if(re.match('^\d+$', str)):
        blk=int(input.get())
        res= inquiry_by_blk(blk,infos )
        print res[1]        
        input.set(res[0]+ ":  " + repr(res[1]))
    else:
        f=open(str,'r')        
        lines=f.readlines() 
        f.close()       
        results=[]
        for l in lines:
            blk=int(l)
            res= inquiry_by_blk(blk,infos )
            if res:                
                results.append(res[0]+ ":  " + repr(res[1]) + os.linesep )
        print 
        result_file= open(os.path.dirname(str) + os.path.sep + 'result.txt', 'w')
        result_file.writelines(results)        
        result_file.close() 

                    
root = Tkinter.Tk()
Tkinter.Label(root,text="""
在输入框中提供块号信息文件的绝对路径：
块号信息文件格式：
file_path_in_device  start_blkno1 end_blkno1 [start_blkno2 end_blkno2]
例子：/system/bin/debuggerd 0 8192 12288 20480
""", 
justify='left').pack()

#输入框用来获取块号文件的绝对路径
e=Tkinter.StringVar()
Tkinter.Entry(root,width='80',textvariable = e ).pack()
e.set("输入块号文件绝对路径")
Tkinter.Button(root,text="提取块号信息", command=partial(process_file,e, gFileInfos)).pack()

# 查询
f=Tkinter.StringVar()
Tkinter.Entry(root,width='80',textvariable = f ).pack()
Tkinter.Button(root,text="查询", command=partial(inquiry_file, f, gFileInfos)).pack()
f.set("输入块号/或文件查询")


Tkinter.mainloop()

