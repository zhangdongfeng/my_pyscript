#-*- coding: utf-8 -*-

import os, sys
from functools import partial
import re
import tkFileDialog
import Tkinter as tk
import string
import pexpect
import time
import tkMessageBox
       
SH='^sh.*'

class ManifestXml(object):
    def __init__(self, root, prefix, branch):
        self.prefix = prefix
        self.root = root
        self.branch = branch
        self.xml_file = root + prefix + '.repo/manifests/' + branch + '.xml'
        self.lines = []
        self.non_tb_repos=[]
        self.tb_repos=[]
        self.all_projects =[]
        print self.xml_file 
        self.extract_repos()
        
        pass
    def get_repo_revision(self, repo):
        
        for l in self.lines:
            mat = re.search(repo, l)
            if(mat):
                print l
                print re.search('revision=\"(\S+)\"', l).group(1)
                return  re.search('revision=\"(\S+)\"', l).group(1)
         
    def add_tb_repo(self,repo):
        #<project name="device/actions/prebuilt/utils" revision="e3606534a0f312956733d52f524bc95d66450c3f"/>
        af = open(self.xml_file, 'wb')        
        find = False
        for l in self.lines:
            mat = re.findall('"' + repo + '"', l)
            if mat:
                find = True
                l = re.sub('revision=\"\S+\"', 'revision=\"refs/heads/zh/' +self.branch +  '\"', l, 1)
                print l
            af.writelines(l)
        af.close()
        self.extract_repos()
        if find:
            return self.root + self.prefix + '.repo/manifests/'  
        

    def get_prefix(self):
        return self.prefix
    def get_tb_repos(self):
        return self.tb_repos
    def get_all_projects(self):
        return self.all_projects
    def get_non_tb_repos(self):
        return self.non_tb_repos
    def extract_repos(self):
        af = open(self.xml_file)
        repos = self.lines =af.readlines();
        af.close()        
        
        tb_repos= [ r for r in repos if r.find("project name=") >= 0 and r.find("TB_") >= 0 ]
        non_tbs= [ r for r in repos if r.find("project name=") >= 0 and not r.find("TB_") >= 0 ]
        all_repos = [ r for r in repos if r.find("project name=") >= 0 ]
        
        for r in all_repos:
            mat =  re.match('\s*<project name=\"(\S+)\"\s+.*', r)
            self.all_projects.append(mat.group(1))
            
        for r in tb_repos:            
            if r.find("path") >= 0:
                mat =  re.match('\s*<project name=\"(\S+)\"\s*path=\"(\S+)\"', r)
                self.tb_repos.append( self.prefix + mat.group(2))
            else:
                mat =  re.match('\s*<project name=\"(\S+)\".*', r)
                self.tb_repos.append( self.prefix + mat.group(1))
        for r in non_tbs:                
            if r.find("path") >= 0:
                mat =  re.match('\s*<project name=\"(\S+)\"\s*path=\"(\S+)\"', r)
                self.non_tb_repos.append(self.prefix + mat.group(2))
            else:
                mat =  re.match('\s*<project name=\"(\S+)\".*', r)
                self.non_tb_repos.append(self.prefix + mat.group(1))
                
class GitExeEnv(object):
    def __init__(self, logfile):
        self.child = pexpect.spawn('sh')        
        self.child.logfile = logfile 
        self.child.timeout = 60 
        self.child.searchwindowsize=200000      
        pass
    def printlog(self, index):  
        print 'index= ' + str(index)       
        #print self.child.before + self.child.after                       
    def printnull(self, index):            
        pass 
    
    def merge_repo(self, path, rev, branch):
        gitcmds=[]
        c1 = 'cd ' + path
        c2 = 'sh'
        c3 = self.printlog
        gitcmds.append([c1,c2,c3])                                
        c1 = 'git fetch gl5202' 
        c2 = ['.*From fwgitsrv.*', 'sh']
        c3 = self.printlog                
        gitcmds.append([c1,c2,c3])   

        c1 = 'git branch -a'
        c2 = '.*' + branch + '.*'
        c3 = self.printlog
        gitcmds.append([c1,c2,c3])
        
        c1 = 'git checkout -b merge  remotes/gl5202/zh/' + branch
        c2 = 'Switched to.*'
        c3 = self.printlog

        gitcmds.append([c1,c2,c3]) 
        
        
        
        
        def merge_complete(index):
            if index == 1:
                gitcmds = []
                c1='\x18'
                c2 = '.*Merge made by the.*'
                c3 = self.printlog
                gitcmds.append([c1,c2,c3])
                self.exec_sh_cmds(gitcmds)
        c1 = 'git merge  -n ' + rev
        c2 = ['.*Merge commit.*'+rev+'.*', '.*Fast-forward.*']
        c3 = merge_complete
        gitcmds.append([c1,c2,c3])  
        
        #c1 = 'git push gl5202 merge:refs/heads/zh/TB_121220_opt__TAG_GS702A_4110_121219'
        #c2 = [r'Everything up-to-date', r'To git@fwgitsrv:']
        
        
        self.exec_sh_cmds(gitcmds)
        pass
    def prepare_push_xml_file(self, path):
        gitcmds=[]
        c1 = 'cd ' + path 
        c2 = 'sh'
        c3 = self.printlog
        gitcmds.append([c1,c2,c3])                                
        c1 = 'git pull  origin GS702A_Integration' 
        c2 = r'From fwgitsrv:ZH/actions/GL5202/.*'
        c3 = self.printlog                
        gitcmds.append([c1,c2,c3]) 
        
        c1 = 'git pull  origin GS702A_Integration' 
        c2 = '.*Already up-to-date.*'
        c3 = self.printlog                
        gitcmds.append([c1,c2,c3]) 
        
        self.exec_sh_cmds(gitcmds)
    
        
    def download(self,path, tag, projects):        
        def asrcinit(path, tag):
            gitcmds=[]
            c1 = 'cd ' + path 
            c2 = 'sh'
            c3 = self.printlog
            gitcmds.append([c1,c2,c3])
            
            c1 = 'asrcinit'
            c2 = '.*Resolving deltas.*'
            c3 = self.printlog
            gitcmds.append([c1,c2,c3])        
            
            self.exec_sh_cmds(gitcmds)        
            
            print os.listdir(path)
            time.sleep(10)
            af = open(path +'/ENV', 'rw+')  
            lines = af.readlines()
            af.close()
            af = open(path +'/ENV', 'wb')  
            for l in lines:
                r = None
                if re.search(r'GS702A_android-4.1.1_r1.xml', l  ):                            
                    l = re.sub(r'GS702A_android-4.1.1_r1.xml',tag +'.xml' , l )
                else:
                    if re.search(r'GS702A_Integration.xml', l):               
                        l = re.sub(r'GS702A_Integration.xml', tag + '.xml', l)
                af.writelines(l)
            af.close()
            
        def srcmanager_init():        
            gitcmds=[]
            c1 = 'cd ' + path 
            c2 = 'sh'
            c3 = self.printlog
            gitcmds.append([c1,c2,c3])
            
            c1 = './srcmanager.sh init'
            c2 = 'Your Name  .*'
            gitcmds.append([c1,c2,c3])
            
            c1 = ''
            c2 = 'Your Email.*'
            gitcmds.append([c1,c2,c3])
            
            c1 = ''
            c2 = 'is this correct.*'
            gitcmds.append([c1,c2,c3])
            
            c1 = 'y'
            c2 = 'Your Name  .*'
            gitcmds.append([c1,c2,c3])
            
            
            c1 = ''
            c2 = 'Your Email.*'
            gitcmds.append([c1,c2,c3])
            
            c1 = ''
            c2 = 'is this correct.*'
            gitcmds.append([c1,c2,c3])
            
            c1 = 'y'
            c2 = 'sh'
            gitcmds.append([c1,c2,c3])        
            self.exec_sh_cmds(gitcmds)
           
    
        def download_quick():
            gitcmds=[]
            c1 = 'cd ' + path 
            c2 = 'sh'
            c3 = self.printlog
            gitcmds.append([c1,c2,c3])
            self.exec_sh_cmds(gitcmds)                       
            c1 = './srcmanager.sh sync'
            c2 = '.*reading config .*'
            gitcmds.append([c1,c2,c3])
            self.exec_sh_cmds(gitcmds) 
            #self.child.sendline(c1)
            i = 0
            for p in range(len(projects)):                
                i+=1
                print i
                index = self.child.expect(['.*Initializing project.*', '.*finish.*'])
                v = projects[index]
                if index == 1 and i > 360:
                    print ' download done'
                    break
                print v
                print index
                print len(projects)
                
        def download_code():
            print projects
            gitcmds=[]
            c1 = 'cd ' + path 
            c2 = 'sh'
            c3 = self.printlog
            gitcmds.append([c1,c2,c3])
            self.exec_sh_cmds(gitcmds)                       
            c1 = './srcmanager.sh sync'
            c2 = '.*reading config .*'
            gitcmds.append([c1,c2,c3])
            self.exec_sh_cmds(gitcmds) 
            #self.child.sendline(c1)
            i = 0
            expect_list = ['.*Initializing project '+p + '.*'  for p in projects ]
            
            for p in range(len(expect_list)):                
                i+=1
                print i
                index = self.child.expect(expect_list)
                v = expect_list[index]                
                expect_list.remove(v)
                
                print v
                print index
                print len(expect_list)
                
            
            print expect_list
                
                 
            
        self.child.timeout = 900    
        asrcinit(path,tag)  
        srcmanager_init()
        download_quick()
        print 'download done'
        pass
        
    def push_xml_file(self, path, comment):  
        gitcmds=[]
        def gitpushxml(index):                        
            if index == 1:                
                c1 = 'git push origin HEAD:GS702A_Integration'
                c2 = ['.*push successfull.*', '.*Everything up-to-date.*']
                c3 = self.printlog
                cmds=[]
                cmds.append([c1,c2,c3]) 
                self.exec_sh_cmds(cmds)
        c1 = 'cd ' + path 
        c2 = 'sh'
        c3 = self.printlog
        gitcmds.append([c1,c2,c3])  
        
        c1 = 'git commit -am \"'  + comment + '\"'
        c2 = '.*' + comment + '.*'
        c3 = gitpushxml
        gitcmds.append([c1,c2,c3])        
        self.exec_sh_cmds(gitcmds)
        
        print path;
        pass
    def push_repo_branch(self,repo):
        gitcmds=[]
        c1 = 'cd ' + repo[0] + repo[1] 
        c2 = 'sh'
        c3 = self.printlog
        gitcmds.append([c1,c2,c3]) 

        c1 = 'git push gl5202 HEAD:refs/heads/zh/' + repo[2]
        c2 = ['.*new branch.*', '.*Everything up-to-date.*']
        c3 = self.printlog
        gitcmds.append([c1,c2,c3])        
        self.exec_sh_cmds(gitcmds)
        pass
    
    def push_merge_repo(self, repo):
        gitcmds=[]
        c1 = 'cd ' + repo[0] + repo[1] 
        c2 = 'sh'
        c3 = self.printlog
        gitcmds.append([c1,c2,c3]) 
        
        def push(index):
            if index == 1:
                gitcmds=[]
                c1 = 'git push gl5202 merge:refs/heads/zh/' + repo[2]
                c2 = ['.*new branch.*', '.*Everything up-to-date.*']
                c3 = self.printlog
                gitcmds.append([c1,c2,c3])
                
                c1 = 'git checkout remotes/gl5202/zh/' + repo[2]
                c2 = 'HEAD is now at .*'
                c3 = self.printlog
                gitcmds.append([c1,c2,c3])    
                   
                c1 = 'git branch -d merge'
                c2 = '.*Deleted branch merge.*'
                c3 = self.printlog
                gitcmds.append([c1,c2,c3])                    
                self.exec_sh_cmds(gitcmds)
            else:
                print "!!!!! push merge repo fail:" 
                print  repo[0] + repo[1]
            
        c1 = 'git status '
        c2 = ['.*nothing to commit, working directory clean.*', '.*nothing added to commit.*']
        c3 = push
        gitcmds.append([c1,c2,c3])
        self.exec_sh_cmds(gitcmds)
        pass
    
    def rebase_repo(self, repo):
        gitcmds=[]
        c1 = 'cd ' + repo[0] + repo[1]
        c2 = 'sh'
        c3 = self.printlog
        gitcmds.append([c1,c2,c3])                                
        c1 = 'git fetch gl5202' 
        c3 = self.printnull                
        gitcmds.append([c1,c2,c3])   
        
        def gitcheckout(index):                        
            if index == 1:                
                c1 = 'git checkout remotes/gl5202/zh/' + repo[2]
                c2 = 'HEAD is now at .*'
                c3 = self.printlog
                cmds=[]
                cmds.append([c1,c2,c3]) 
                self.exec_sh_cmds(cmds)

        c1 = 'git branch -a'
        c2 = '.*' + repo[2] + '.*'
        c3 = gitcheckout
        gitcmds.append([c1,c2,c3])        
        self.exec_sh_cmds(gitcmds)
        
    def get_git_log(self, repos):        
        for repo in repos:
            gitcmds = []            
            c1 = 'cd ' + repo[0] + repo[1]
            c2 = 'sh'
            c3 = None                       
            gitcmds.append([c1,c2,c3]) 
            c1 = 'git log  -1'
            c2 = 'sh'           
            gitcmds.append([c1,c2,c3]) 
            self.exec_sh_cmds(gitcmds)
   
    def exec_sh_cmds(self, cmds):  
        for c in cmds:           
            self.child.sendline(c[0])   
            print c[0] 
            expect = []
            if type(c[1]) == type(''):
                expect = [ pexpect.TIMEOUT, c[1]] 
            else:
                expect  =[ pexpect.TIMEOUT ] + c[1]                
            index =self.child.expect(expect)
            #time.sleep(5)
            if c[2]:
                  c[2](index)
                           
class Project(object):
    def __init__(self, root_path):
        self.root = root_path 
        self.branch=''
        self.android_mf=None
        self.leopard_mf=None
        self.base_tag='not found'
        pass
    def get_branch(self):
        return self.branch
    def get_root(self):
        return self.root
    
    def get_all_projects(self):
        list = self.android_mf.get_all_projects() + self.leopard_mf.get_all_projects()
        return list        
        
    def get_tb_repos(self):
        list = self.android_mf.get_tb_repos() + self.leopard_mf.get_tb_repos()
        return [[self.root,repo,self.branch] for repo in list]        
    def get_non_tb_repos(self):
        list = self.android_mf.get_non_tb_repos() + self.leopard_mf.get_non_tb_repos()
        return [[self.root,repo,self.branch] for repo in list]           
    def set_branch(self, branch):
        self.branch = branch
        self.android_mf=ManifestXml(self.root,'/android/',  branch)        
        self.leopard_mf= ManifestXml(self.root,'/leopard/', branch)
        self.parse_base_tag()        
    def add_tb_repo(self,repo):
        if repo.startswith(self.android_mf.get_prefix()):            
            repo =  repo.replace('/android/','')           
            return self.android_mf.add_tb_repo(repo)
        else:
            repo = repo.replace('/leopard/','')
            return self.leopard_mf.add_tb_repo(repo)
    def get_repo_revision(self, repo):
        if repo.startswith(self.android_mf.get_prefix()):            
            repo =  repo.replace(self.android_mf.get_prefix(),'')           
            return self.android_mf.get_repo_revision(repo)
        else:
            repo = repo.replace(self.leopard_mf.get_prefix(),'')
            return self.leopard_mf.get_repo_revision(repo)
        
    def parse_base_tag(self):
        f = open(self.root +  '/android/.repo/manifests/' + self.branch + '.xml')
        lines = f.readlines()
        for l in lines:
            #<!--branch_base_tag=TAG_GS702A_4110_121219-->
            tag = re.search('branch_base_tag=(\w+)', l)
            if(tag):
                self.base_tag = tag.group(1)
                #print self.base_tag
                break;
        f.close()
    def set_base_tag(self, tag):
        self.base_tag = tag
        f = open(self.root +  '/android/.repo/manifests/' + self.branch + '.xml')
        lines = f.readlines()
        f.close()
        f = open(self.root +  '/android/.repo/manifests/' + self.branch + '.xml', 'wb')
        i=0
        for l in lines:
            i+=1
            if i==6:
                f.writelines('  <!--branch_base_tag=' + tag + '-->')
            f.writelines(l)
        f.close()
        pass
    def get_base_tag(self):
            return self.base_tag
    
class Application(tk.Frame):              
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)   
        self.grid()      
        self.prj_dir = tk.StringVar() 
        self.branch_var = tk.StringVar()  
        self.xml_files=tk.StringVar()
        self.tb_reps=tk.StringVar()
        self.non_tb_reps=tk.StringVar()
        self.tag_var = tk.StringVar()  
        self.rebase_prj = None
        self.rebase_dir = tk.StringVar() 
        self.rebase_tag=''
        
        self.project=None
        #self.prj=''
        #self.branch=''
        #self.android_repos=[]        
        self.createWidgets()
        #self.non_branch_repos=[] 
        
          
       

    def createWidgets(self):
        
        #row 1
        r = 0; c=0
        self.prjLabel= tk.Label(self,text='prjroot:  ' ).grid(row=r,column=c)
        self.prj_dir.set("not set")
        c+=1
        tk.Label(self,textvariable=self.prj_dir).grid(row=r,column=c, columnspan=2)    
        c+=2    
        tk.Button(self,text='select', command = self.get_prj_xml).grid(row = r,column=c)
        #row 1
        r+=1; c=0
        tk.Label(self,text='branchs:').grid(row = r,column=c )
        c+=1
        self.branch_var.set("not set")
        tk.Label(self,textvariable=self.branch_var).grid(row=r,column=c, columnspan=2) 
         #row 1
        r+=1; c=0
        tk.Label(self,text='BranchbaseTag:').grid(row = r,column=c )
        c+=1
        self.tag_var.set("not set")
        tk.Label(self,width=50, textvariable=self.tag_var).grid(row=r,column=c, columnspan=2) 
        c+=2   
        tk.Button(self,text='rebaseToTag', command = self.rebase_TAG).grid(row = r,column=c)       
        
        #row 2
        r+=1; c=0
        tk.Label(self,text='repos:',  ).grid(row = r,column=c)
        c+=1
        self.repBox = tk.Listbox(self, width=40,height=10, listvariable=self.tb_reps)
        self.repBox.grid(row = r,column=c, columnspan=2)
        c+=2
        tk.Button(self,text='add repo', command = self.show_non_tb_repos).grid(row = r,column=c)
        #tk.Button(self,text='select repo', command = self.select_repo).grid(row = 2,column=2)
        #row3 
        r+=1; c=0
        tk.Button(self,text='rebase repo', command = self.select_repo).grid(row = r, column=c)
        c+=1
        tk.Button(self,text='rebase all repo', command = self.rebase_all_repo).grid(row = r, column=c)
        c+=1
        tk.Button(self,text='get gtilog', command = self.get_git_log).grid(row = r, column=c)
    
    def rebase_TAG(self):
        
        ee = GitExeEnv(sys.stdout)
        ee.prepare_push_xml_file(self.project.get_root() + '/android/.repo/manifests/')
        #ee.prepare_push_xml_file(self.project.get_root() + '/leopard/.repo/manifests/')
        
        android_xml = self.project.get_root() + '/android/.repo/manifests/'
        files = os.listdir(android_xml)
        xml_files= [ file for file in files if file.startswith('TAG_')]
        s = ''
        for file in xml_files:
            s += ' '
            s += file            
        self.xml_files.set(s)
        
        self.toplevel= tk.Toplevel()
        self.toplevel.title('select a rebase tag')
        self.tagBox=tk.Listbox(self.toplevel, width=50, listvariable=self.xml_files)
        self.tagBox.grid(columnspan=2)
        
        def check_dir():
            if self.rebase_dir.get() == 'not set':
                tkMessageBox.showerror('select rebase project dir')            
        def pre_dir():
            s = self.tagBox.curselection()[0]
            tag = self.tagBox.get(s)
            print tag
            prj=tkFileDialog.askdirectory(parent=self.toplevel,initialdir='~/', mustexist=False)            
            self.rebase_prj= Project(prj)
            try:
                af = open(prj +'/ENV')                            
                lines = af.readlines()
                af.close()
           
                for l in lines:
                    r = None
                    mat = re.search('ANDROID_MANIFEST=(\S+)\s*', l)
                    if mat:                            
                        rebase_tag=mat.group(1)
                        self.rebase_tag = rebase_tag.split('.')[0]
                if not tag == rebase_tag  :
                    tkMessageBox.showerror('unmatched taq', tag + ' <>'  + rebase_tag)
                    self.rebase_tag = tag.split('.')[0]
            except:
                
                self.rebase_tag = tag.split('.')[0]
                print  'rebase tag: :'  + self.rebase_tag + '  is that correct ?'
            self.rebase_dir.set(prj)
            
        def download():            
            of=open(self.rebase_prj.get_root() + '/gitdownload.txt', 'wb')
            ee = GitExeEnv(of)
            ee.prepare_push_xml_file(self.project.get_root() + '/android/.repo/manifests/')
            #ee.prepare_push_xml_file(self.project.get_root() + '/leopard/.repo/manifests/')
            ee.download(self.rebase_prj.get_root(), self.rebase_tag, self.project.get_all_projects())
            tkMessageBox.showinfo("Git download  complete")
            of.close()           
            
            #print prj
            pass
        def merge_tag():
            
            
            branch = self.project.get_branch()
            self.rebase_prj.set_branch(self.rebase_tag)
            tb_repos = self.project.get_tb_repos()
            print tb_repos
            merge_repos = [(r[1],self.rebase_prj.get_repo_revision(r[1])) for r in tb_repos]
            print merge_repos
            of=open(self.rebase_prj.get_root() + '/gitmerge.txt', 'wb')
            ee = GitExeEnv(of)
            for m in merge_repos:
                ee.merge_repo(self.rebase_prj.get_root() + m[0], m[1], branch )
            print "Git Merge complete"
            tkMessageBox.showinfo("Git Merge complete")    
            
               
            #ee.prepare_push_xml_file(self.project.get_root() + '/android/.repo/manifests/')
            #ee.prepare_push_xml_file(self.project.get_root() + '/leopard/.repo/manifests/')
            #ee.download(prj, tag, self.project.get_all_projects())
            of.close()
            #self.rebase_prj.add_tb_repo(repo)
            pass
        def make():
            pass
        def commit():
            of=open(self.rebase_prj.get_root() + '/gitcommit.txt', 'wb')
            ee = GitExeEnv(of)
            root = self.rebase_prj.get_root()
            c = 'cp ' + root + '/android/.repo/manifests/' +self.rebase_tag + '.xml '  + root + '/android/.repo/manifests/' +self.project.get_branch() + '.xml'
            ee.child.sendline(c)
            c = 'cp ' + root + '/leopard/.repo/manifests/' +self.rebase_tag + '.xml '  + root + '/leopard/.repo/manifests/' +self.project.get_branch() + '.xml'
            ee.child.sendline(c)
            
            c = 'cp ' + self.project.get_root() + '/ENV '   + root + '/ENV' 
            ee.child.sendline(c)
            
            self.rebase_prj.set_branch(self.project.get_branch())
            tb_repos = self.project.get_tb_repos()
            for r in tb_repos:
                self.rebase_prj.add_tb_repo(r[1])
            self.rebase_prj.set_branch(self.project.get_branch())
            tb_repos = self.rebase_prj.get_tb_repos()
            
            self.rebase_prj.set_base_tag(self.rebase_tag)
            
            for r in tb_repos:
                print r
                ee.push_merge_repo(r)
            ee.prepare_push_xml_file(root + '/android/.repo/manifests/')    
            ee.push_xml_file(root + '/android/.repo/manifests/' , "rebase to tag: " + self.rebase_tag)   
            ee.prepare_push_xml_file(root + '/leopard/.repo/manifests/')            
            ee.push_xml_file(root + '/leopard/.repo/manifests/' , "rebase to tag: " + self.rebase_tag)
            of.close()
            pass
        
        def exit():
            
            self.toplevel.destroy()
            if not self.rebase_prj:
                return 
            self.project = self.rebase_prj;
            self.prj_dir.set(self.project.get_root())
            self.branch_var.set(self.project.get_branch())             
            self.non_tb_reps=tk.StringVar()
            self.tag_var.set(self.project.get_base_tag())
            self.rebase_prj = None
            self.rebase_tag=''
            self.update_view_repos()
            pass
        
        tk.Button(self.toplevel,text='prepare dir ', command = pre_dir).grid(row = 0,column=3)
        r = 2; c=0
        self.rebase_dir.set("not set")
        tk.Label(self.toplevel,text="rebase project dir: ").grid(row=r,column=c)
        c+=1
        tk.Label(self.toplevel,textvariable=self.rebase_dir).grid(row=r,column=c, columnspan=2)
        r+=1; c=0
        tk.Button(self.toplevel,text='download ', command = download).grid(row = r,column=c)
        c+=1
        tk.Button(self.toplevel,text='merge branch', command = merge_tag).grid(row = r,column=c)
        c+=1
        tk.Button(self.toplevel,text='make ', command = make).grid(row = r,column=c)
        c+=1
        tk.Button(self.toplevel,text='commit  branch', command = commit).grid(row = r,column=c)
        c+=1
        tk.Button(self.toplevel,text='done', command = exit).grid(row = r,column=c)  
        pass
        
    def show_non_tb_repos(self):
        self.toplevel= tk.Toplevel()
        self.toplevel.title('select a repo')
        repos = self.project.get_non_tb_repos()        
        s = ''
        for r in repos:
            s += ' '
            s += r[1]
        self.non_tb_reps.set(s)
        self.repoBox=tk.Listbox(self.toplevel,width=40,height=30, listvariable=self.non_tb_reps)
        self.repoBox.grid()
        tk.Button(self.toplevel,text='select repo', command = self.add_new_repo).grid(row = 0,column=1)
        pass
    
    def add_new_repo(self):
        s = self.repoBox.curselection()[0]
        repo = self.repoBox.get(s)        
        self.toplevel.destroy()
        of=open(self.project.get_root() + '/gitaddbranch.txt', 'wb')
        ee = GitExeEnv(of)
        ee.prepare_push_xml_file(self.project.get_root() + '/android/.repo/manifests/')
        ee.prepare_push_xml_file(self.project.get_root() + '/leopard/.repo/manifests/')
        xml_path  = self.project.add_tb_repo(repo)        
        if xml_path:
            root = self.project.get_root()
            branch = self.project.get_branch()
            ee.push_xml_file(xml_path, "add branch for " + repo)
            ee.push_repo_branch([root, repo, branch])
            of.close()
            self.project.set_branch(branch)        
            self.update_view_repos()
        pass    
    
    def get_prj_xml(self):        
        prj=tkFileDialog.askdirectory(initialdir='~/', mustexist=True)
        self.project = Project(prj)
                   
        self.prj_dir.set(prj)
        
        android_xml = prj + '/android/.repo/manifests/'
        files = os.listdir(android_xml)
        xml_files= [ file for file in files if file.startswith('TB_')]
        s = ''
        for file in xml_files:
            s += ' '
            s += file            
        self.xml_files.set(s)
        self.toplevel= tk.Toplevel()
        self.toplevel.title('select a branch')
        self.branchBox=tk.Listbox(self.toplevel, width=50, listvariable=self.xml_files)
        self.branchBox.grid()
        tk.Button(self.toplevel,text='select branch', command = self.select_branch).grid(row = 0,column=1)
             
         
    def rebase_all_repo(self):                
        of=open(self.project.get_root() + '/gitrebase.txt', 'wb')
        ee = GitExeEnv(of)
        root = self.project.get_root()
        branch = self.project.get_branch()
        repos = self.project.get_tb_repos()
        for repo in repos:
            ee.rebase_repo(repo )
        of.close()
        
    def get_git_log(self):
        of=open(self.project.get_root() + '/gitlog.txt', 'wb')
        ee = GitExeEnv(of)
        root = self.project.get_root()
        branch = self.project.get_branch()
        repos = self.project.get_tb_repos()
        for repo in repos:
            ee.rebase_repo(repo )
        of.close()
        
    def select_repo(self):
        s = self.repBox.curselection()[0]
        repo= self.repBox.get(s)
        
        root = self.project.get_root()
        branch = self.project.get_branch()
        ee = GitExeEnv(sys.stdout)
        ee.rebase_repo([root,repo,branch]) 
        
    def select_branch(self):
        s = self.branchBox.curselection()[0]
        branch = self.branchBox.get(s).split('.')[0]
        self.branch_var.set(branch) 
        self.toplevel.destroy()
        self.project.set_branch(branch)
        self.tag_var.set(self.project.get_base_tag())
        #prj = self.prj
        self.update_view_repos()
        
    def update_view_repos(self):
        tb_repos = self.project.get_tb_repos()        
        s=''
        for r in tb_repos:
            s +=' '
            s += r[1]
        self.tb_reps.set(s)
    

 
        
app = Application()                       
app.master.title('branch ')    
app.mainloop()    
